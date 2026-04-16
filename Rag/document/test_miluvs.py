


# 不通过统一句柄，用户可以直接调用其方法进行操作。
from pymilvus import (
    connections,
    utility,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
)

def create_collection():
    """创建表  """
    # 1、定义字段
    fileds=[
        FieldSchema(name="id",dtype=DataType.INT64,is_primary=True,auto_id=True),
        #存储分块的文本内容
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=5000),
        # 存储向量数据
        FieldSchema(name="dense", dtype=DataType.FLOAT_VECTOR,dim=1024),
        FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR),
        # 存储分块的元数据
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="filename", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="filetype", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=1000),
        FieldSchema(name="category_depth", dtype=DataType.INT64, max_length=1000),
    ]
    # 创建collection 表结构对象
    schema = CollectionSchema(fileds)

    if utility.has_collection(COLLECTION_NAME):  # 判断表是否存在
        Collection(COLLECTION_NAME).drop()  # 删除表
        print(f"{COLLECTION_NAME}已经存在， 删除表")

    col = Collection(name=COLLECTION_NAME, schema=schema)

    print(f"创建表成功：{COLLECTION_NAME}")

    # 在sparse字段里面加入倒排索引，加快索引速度
    sparse_index = {"index_type":"SPARSE_INVERTED_INDEX","metric_type":"IP"}
    col.create_index("sparse",sparse_index)
    # 表示让miluvs自动最合适的索引类型，如HNSW,IVF等，HNSW,IVF是ANN算法的优化，ANN是KNN的优化
    dense_index = {"index_type":"AUTOINDEX","metric_type":"IP"}
    col.create_index("dense", dense_index)

    col.load() # 将集合数据加载到内存中，以便于做后面的查询操作




COLLECTION_NAME = "test"
if __name__ == "__main__":
    # 连接milvus 数据库
    connections.connect(uri="http://127.0.0.1:19530")
    col = None
    if utility.has_collection(COLLECTION_NAME):  # 判断表是否存在
        col = Collection(COLLECTION_NAME)  # 获取表对象
    create_collection()




