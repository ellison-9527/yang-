
"""解析pdf内容"""
# 导入pdf加载器
from langchain_community.document_loaders import PyPDFLoader
"""
    LangChain中的核心数据结构 :
        Document(
                page_content="文本内容",
                metadata={"page": 1, "source": "..."}
                )
)
"""
# 实例化文档加载器对象
loader =  PyPDFLoader("../data/layout-parser-paper.pdf")

# 返回一个列表，每个元素对应每一页，一页一页进行解析，每一页为一个document对象
docs = loader.load()
print(f"文档类型:",type(docs[0]))
print(f"doc的数量:",len(docs))

print("*"*50)
print(docs[0].page_content)
print(docs[0].metadata)




