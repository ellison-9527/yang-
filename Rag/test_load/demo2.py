"""
    结构化解析pdf 中的目录结构，表、图片、代码
"""
import json
from langchain_unstructured import UnstructuredLoader

# 创建文档加载器对象
loader =  UnstructuredLoader(
    file_path = "../data/layout-parser-paper.pdf",
    strategy = 'hi_res', # 高精度（可选 'fast', 'ocr_only'）
    partition_via_api=True, # 是否调用API接口
    coordinates=True,  # 是否返回文档的坐标框，左上角和右下角坐标
    api_key="IhWKAZRBmZ14c8tmCsOLabqwIKLJ2e"
)

counter = 0
for doc in loader.lazy_load():
    print(doc.page_content)
    print(doc.metadata)
    json_file_name = str(doc.metadata.get('page_number'))+'_'+str(counter) + '.json' # 以页码_分块数量.json组成
    counter += 1
    with open(f'../output/{json_file_name}',encoding='utf-8',mode='w') as file:
        #  doc.model_dump()  可以将docment对象转换为字典对象
        json.dump(doc.model_dump(),file,ensure_ascii=False,indent=4)

