
import json
from langchain_core.documents import Document
"""
    加载文件里面的内容还原成document对象
"""
if __name__ == "__main__":
    with open("../output/1_0.json",'r',encoding='utf-8') as file:
        data =  json.load(file)  # 将文件内容转换为字典对象
        doc = Document(page_content=data.get("page_content"),metadata=data.get("metadata"))
    print(doc)