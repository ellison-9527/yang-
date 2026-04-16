

from langchain_community.document_loaders import UnstructuredMarkdownLoader

# 实例化markdown的加载器对象
loader =  UnstructuredMarkdownLoader(
    file_path="../data/md/operational_faq.md",
    mode = 'elements', # 按元素进行分块
    strategy='fast',
    partition_via_api=True,
    api_key="IhWKAZRBmZ14c8tmCsOLabqwIKLJ2e"
)

docs = loader.load()
print(f"doc数量：",len(docs))

for i in range(10):
    print(docs[i].page_content)
    print(docs[i].metadata)
    print('*'*50)