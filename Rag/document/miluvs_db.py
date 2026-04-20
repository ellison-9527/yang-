import time
from typing import List
from langchain_core.documents import Document
# transformers-4.44.2 FlagEmbedding==1.3.5
from pymilvus import model
# 没有统一句柄，用户可以直接调用其方法进行操作。
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)
from pymilvus import (
    AnnSearchRequest,
    WeightedRanker,
    RRFRanker
)
from scipy.sparse import csr_matrix
from pymilvus.model.reranker import BGERerankFunction
import torch

from Rag.document.markdown_parser import MarkdownParser

MILVUS_URI = "http://127.0.0.1:19530"
COLLECTION_NAME = "test2"
def csr_to_sparse_dict(csr_vec: csr_matrix) -> dict:
    """将单行的 csr_matrix 转换为 {index: value} 格式的字典"""
    # 提取非零元素的列索引和对应的值
    indices = csr_vec.indices
    values = csr_vec.data

    # 构建字典
    sparse_dict = {int(idx): float(val) for idx, val in zip(indices, values)}
    return sparse_dict

class MilvusVectorSave:
    """把新的document数据插入到数据库中"""

    def __init__(self) -> object:
        """自定义collection的索引 Milvus对象"""
        # Connect to Milvus given URI
        connections.connect(uri=MILVUS_URI)
        # 可以同时生成稀疏和稠密向量
        # 本地地址 ： C:\Users\<你的用户名>\.cache\huggingface\hub\models--BAAI--bge-m3
        self.bge_m3_ef = model.hybrid.BGEM3EmbeddingFunction(
            model_name='BAAI/bge-m3',  # Specify the model name
            device="cuda" if torch.cuda.is_available() else "cpu",  # 运行设备
            use_fp16=False
        )
        # 实例化一个重排模型
        self.rerank = BGERerankFunction(
            model_name="BAAI/bge-reranker-v2-m3",
            device="cuda" if torch.cuda.is_available() else "cpu",  # 运行设备
            use_fp16=False,
            batch_size=32,
            normalize=True
        )
        self.col = None
        if utility.has_collection(COLLECTION_NAME):
            self.col = Collection(COLLECTION_NAME)

    def create_collection(self):

        # Specify the data schema for the new Collection
        # 定义字段，用于存储和管理混合搜索所需的数据
        fields = [
            # Use auto generated id as primary key
            FieldSchema(
                name="id", dtype=DataType.INT64, is_primary=True, auto_id=True,
            ),
            # Store the original text to retrieve based on semantically distance
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=6000),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="filename", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="filetype", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="category_depth", dtype=DataType.INT64),
            # Milvus now supports both sparse and dense vectors,
            # we can store each in a separate field to conduct hybrid search on both vectors
            FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR),
            FieldSchema(name="dense", dtype=DataType.FLOAT_VECTOR, dim=1024),
        ]

        # Create collection结构
        schema = CollectionSchema(fields)
        if utility.has_collection(COLLECTION_NAME):
            Collection(COLLECTION_NAME).drop()
            # 使用 logger 记录日志
            print(f"{COLLECTION_NAME} 已存在，删除集合")
        # Strong consistency waits for all loads to complete, adding latency with large datasets
        # col = Collection(col_name, schema, consistency_level="Strong")
        self.col = Collection(COLLECTION_NAME, schema)

        # To make vector search efficient, we need to create indices for the vector fields
        # 表示使用倒排索引（Inverted Index）来处理稀疏向量。
        sparse_index = {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"}
        self.col.create_index("sparse", sparse_index)
        #  表示让 Milvus 自动选择最适合的索引类型（如 HNSW、IVF 等）。 HNSW、IVF是ANN算法的优化
        dense_index = {"index_type": "AUTOINDEX", "metric_type": "IP"}
        self.col.create_index("dense", dense_index)
        print(f"{COLLECTION_NAME} 创建成功")
        self.col.load()  # 将集合加载到内存中，使索引生效并准备好接受查询请求

    def doc_to_embed(self,docs: List[str]):
        """把新的document生成稠密和稀疏向量"""
        # print("生成向量......")

        # Generate embeddings using BGE-M3 model
        docs_embeddings = self.bge_m3_ef(docs)
        # print(f"Dense dim: {self.bge_m3_ef.dim['dense']}")
        # print(f"sparse dim : {self.bge_m3_ef.dim['sparse']}")
        # print(f"data number : {len(docs_embeddings['dense'])}")
        return docs_embeddings

    def add_documents(self, datas: List[Document]):

        # 取出文本
        docs = [data.page_content for data in datas]
        # 生成向量
        docs_embeddings = self.doc_to_embed(docs)

        # 批量转换所有稀疏向量 将csr_matrix 转换为 {index: value}
        sparse_dicts = [csr_to_sparse_dict(vec) for vec in docs_embeddings["sparse"]]



        """把新的document保存到Milvus中"""
        bs = 5   # 一次性插入20个数据
        for i in range(0, len(datas), bs):
            batched_entities = [
                docs[i: i + bs],  # 大于1w的数据建议使用numpy高效处理数据
                [data.metadata["category"] for data in datas[i:i + bs]],
                [data.metadata["source"] for data in datas[i: i + bs]],
                [data.metadata["filename"] for data in datas[i: i + bs]],
                [data.metadata["filetype"] for data in datas[i: i + bs]],
                [data.metadata.get("title") for data in datas[i: i + bs]],
                [data.metadata["category_depth"] for data in datas[i: i + bs]],
                sparse_dicts[i: i + bs],
                docs_embeddings["dense"][i: i + bs],

            ]
            # print(batched_entities)
            self.col.insert(batched_entities)  # 一次性插入bs条数据
        self.col.flush()  # 刷新缓存
        print("Number of entities inserted:", self.col.num_entities)

    def dense_search(self,query_dense_embedding,limit=10,expr=None):
        """
        :param query_dense_embedding:  需要进行匹配的嵌入向量
        :param limit:  返回最大相似结果个数
        :param expr:   过滤条件
        :return:  检索到的文档内容
        """

        res =  self.col.search(
            [query_dense_embedding],# 查询向量
            anns_field = "dense", # 指定搜索的目标字段
            limit = limit,
            output_fields=["text"], # 指定返回结果中包含的字段
            param={"metric_type": "IP", "params": {}},
            expr=expr
        )[0]
        return [ hit.get("text") for hit in res ]

    def sparse_search(self, query_sparse_embedding, limit=10, expr=None):
        """
        :param query_sparse_embedding:  需要进行匹配的嵌入向量
        :param limit:  返回最大相似结果个数
        :param expr:   过滤条件
        :return:  检索到的文档内容
        """

        res = self.col.search(
            [query_sparse_embedding],  # 查询向量
            anns_field="sparse",  # 指定搜索的目标字段
            limit=limit,
            output_fields=["text"],  # 指定返回结果中包含的字段
            param={"metric_type": "IP", "params": {}},
            expr=expr
        )[0]
        return [hit.get("text") for hit in res]

    def hybird_search(self,query_dense_embedding,query_sparse_embedding,sparse_weight,dense_weight,limit=10,expr=None):
        """
        :param query_dense_embedding:    问题对应的密集向量
        :param query_sparse_embedding:   问题对应的稀疏向量
        :param sparse_weight:     语义检索的权重
        :param dense_weight:      关键字检索权重
        :param limit:             返回最大相似结果个数
        :param expr:               过滤条件
        :return:
        """
        # 创建一个密集向量请求对象
        dense_req =  AnnSearchRequest(
            [query_dense_embedding],
            "dense",{"metric_type": "IP", "params": {}},limit=limit*2,expr=expr)
        # 创建一个稀疏向量请求对象
        sparse_req = AnnSearchRequest(
            [query_sparse_embedding],
            "sparse", {"metric_type": "IP", "params": {}}, limit=limit * 2, expr=expr)
        # 创建权重排名对象
        # rerank =  WeightedRanker(sparse_weight,dense_weight)

        rerank =  RRFRanker(k=60)


        res = self.col.hybrid_search(
            [dense_req,sparse_req],
            rerank=rerank,
            limit=limit,
            output_fields=["text"]
        )[0]
        return [hit.get("text") for hit in res]

    def reRank_model(self,query,docs,top_k=5,score_thres=0.2):
        """将问题和问题给到重排模型，对这些文档依次进行打分，将分数高的排在前面，文档数量最后不要超过10"""
        results =  self.rerank(
            query=query,
            documents=docs,
            top_k=top_k,
        )
        rank_doc = []
        for result in results:
            if result.score > score_thres:
                rank_doc.append(result.text)
        return  rank_doc

    # 解析文件内容
if __name__ == '__main__':
    # file_path = r'C:\Users\33122\Desktop\assis_bk\Rag\data\md\operational_faq.md'
    # parser = MarkdownParser()
    # docs = parser.parse_markdown_to_documents(file_path)
    # print(docs[:20])

    # 写入Milvus数据库
    mv = MilvusVectorSave()
    # mv.create_collection()
    # mv.add_documents(docs)

    while True:
        user = input("请输入：")

        query_embeddings = mv.doc_to_embed([user])
        # print(query_embeddings['dense'])
        # res = mv.dense_search(query_embeddings['dense'][0],expr="categoyr=='content'")
        # print("密集向量检索到的结果为:\n", len(res))
        # print("密集向量检索到的结果为:\n", res)
        # res = mv.sparse_search(query_embeddings['sparse'][[0]])
        # print("关键字匹配到的结果为:\n", len(res))
        # print("关键字匹配到的结果为:\n", res)

        hybird_results =  mv.hybird_search(
            query_embeddings['dense'][0],
            query_embeddings['sparse'][[0]],
            sparse_weight=0.3,
            dense_weight=0.7,
        )
        # print("\n混合检索===============================")
        # for result in hybird_results:
        #     print(result)

        results = mv.reRank_model(user,hybird_results)
        print(len(results))
        for result in results:
            print(result)

        print("\n===============================")
