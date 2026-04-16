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
        print("生成向量......")

        # Generate embeddings using BGE-M3 model
        docs_embeddings = self.bge_m3_ef(docs)
        print(f"Dense dim: {self.bge_m3_ef.dim['dense']}")
        print(f"sparse dim : {self.bge_m3_ef.dim['sparse']}")
        print(f"data number : {len(docs_embeddings['dense'])}")
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



if __name__ == '__main__':
    # 解析文件内容
    file_path = r'C:\Users\33122\Desktop\assis_bk\Rag\data\md\operational_faq.md'
    parser = MarkdownParser()
    docs = parser.parse_markdown_to_documents(file_path)
    print(docs[:20])

    # 写入Milvus数据库
    mv = MilvusVectorSave()
    mv.create_collection()
    mv.add_documents(docs)


