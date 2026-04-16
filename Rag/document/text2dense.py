# pip install --upgrade pymilvus "pymilvus[model]"
# transformers==4.44.2 FlagEmbedding==1.3.5
from pymilvus import model
import torch


def create_embeding_model():
    """创建嵌入模型，能同时生成密集向量和稀疏向量"""
    #  本地地址 ： C:\Users\<你的用户名>\.cache\huggingface\hub\models--BAAI--bge-m3
    return model.hybrid.BGEM3EmbeddingFunction(
        model_name="BAAI/bge-m3",  # 指定模型名字
        device="cuda" if torch.cuda.is_available() else "cpu",
        use_fp16=False
    )

if __name__ == '__main__':
    bge_m3_model = create_embeding_model()
    from langchain_community.document_loaders import UnstructuredMarkdownLoader
    # 实例化markdown的加载器对象
    loader = UnstructuredMarkdownLoader(
        file_path="../data/md/operational_faq.md",
        mode='elements',  # 按元素进行分块
        strategy='fast',
        partition_via_api=True,
        api_key="IhWKAZRBmZ14c8tmCsOLabqwIKLJ2e"
    )
    docs_lc = loader.load()
    print(f"doc数量：", len(docs_lc))

    # 取出文本
    docs = [data.page_content  for data in docs_lc]   # 获取文档内容 每一个元素为字符串类型
    print(docs)
    print("生成向量..........")

    docs_embeddings = bge_m3_model(docs)
    print(f"data number : {len(docs_embeddings['dense'])}")
    print(f"第一个文档对应的密集向量是: {docs_embeddings['dense'][0]}")
    print(f"第二个文档对应的密集向量是: {docs_embeddings['dense'][1]}")
    # print(f"Dense Dim {bge_m3_model.dim['dense']}")  # 密集向量的维度为1024

