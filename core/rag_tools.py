from langchain_core.tools import tool
from Rag.document.miluvs_db import MilvusVectorSave
mv = MilvusVectorSave()

@tool
def retriever_tool(query:str) -> list:
    """可以获取miluvs相关的帮助文档"""

    # 加载数据到内存
    mv.col.load()  #  将集合加载到内存中，使索引生效并准备好接受查询请求
    query_embeddings = mv.doc_to_embed([query])
    hybird_results = mv.hybird_search(
        query_embeddings['dense'][0],
        query_embeddings['sparse'][[0]],
        sparse_weight=0.3,
        dense_weight=0.7,
    )
    results = mv.reRank_model(query, hybird_results)

    return results

if __name__ == "__main__":
    print(retriever_tool.run("docker是不是miluv的唯一运行方式"))