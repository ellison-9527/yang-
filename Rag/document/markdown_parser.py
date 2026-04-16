from typing import List
from langchain_experimental.text_splitter import SemanticChunker

from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_core.documents import Document

from langchain_community.embeddings import ZhipuAIEmbeddings


class MarkdownParser:
    """
    专门负责markdown文件的解析和切片
    """
    def __init__(self):
        openai_embedding = ZhipuAIEmbeddings(
            model="embedding-3", # 出现警告cl100k_base，这个是默认的分词方案，智普有自己的分词方案
            api_key="89537a50b18a4644a6c8829d8abc6493.w7oL0reCLw9qiVCL",
        )

        self.text_splitter = SemanticChunker(  # openai提供的语义切割的函数
            openai_embedding, breakpoint_threshold_type="percentile",
        )

    def text_chunker(self, datas: List[Document]) -> List[Document]:
        new_docs = []
        for d in datas:
            if len(d.page_content) > 1000:  # 内容超出了阈值，则按照语义再切割
                new_docs.extend([
                    Document(page_content=doc.metadata.get('title', '') + doc.page_content,
                             metadata=doc.metadata,
                             id=doc.id)
                    for doc in self.text_splitter.split_documents([d])
                ])
                continue
            new_docs.append(d)
        return new_docs


    def parse_markdown_to_documents(self, md_file: str, encoding='utf-8') -> List[Document]:
        documents = self.parse_markdown(md_file)  # 1、 将markdown文件解析成document对象
        # log.info(f'文件解析后的docs长度: {len(documents)}')
        print(f'文件解析后的docs长度: {len(documents)}')

        merged_documents = self.merge_title_content(documents)  # 2、将标题和文本块合并，建立文本块与目录的结构关系
        # log.info(f'文件合并后的长度: {len(merged_documents)}')
        print(f'文件合并后的长度: {len(merged_documents)}')

        chunk_documents = self.text_chunker(merged_documents)   # 3、语义切割
        # log.info(f'语义切割后的长度: {len(chunk_documents)}')
        print(f'语义切割后的长度: {len(chunk_documents)}')
        return chunk_documents

    def parse_markdown(self, md_file: str) -> List[Document]:
        loader = UnstructuredMarkdownLoader(
            file_path=md_file,
            mode='elements',
            strategy='fast'
        )
        docs = []
        for doc in loader.lazy_load():
            docs.append(doc)

        return docs

    def merge_title_content(self, datas: List[Document]) -> List[Document]:
        merged_data = []  # 存储最终结果
        parent_dict = {}  # 是一个字典，保存所有的父document， key为当前父document的ID
        for document in datas:
            metadata = document.metadata
            if 'languages' in metadata: # 移除languages键
                metadata.pop('languages')

            parent_id = metadata.get('parent_id', None)
            category = metadata.get('category', None)
            element_id = metadata.get('element_id', None)

            # 无父document且是文档时直接添加到结果。说明为独立内容文档
            if category == 'NarrativeText' and parent_id is None:  # 是否为：内容document
                merged_data.append(document)
            if category == 'Title': # 是否为：标题document 存储到字典中
                document.metadata['title'] = document.page_content
                if parent_id in parent_dict: # 存在父级标题，构建层级结构
                    document.page_content = parent_dict[parent_id].page_content + ' -> ' + document.page_content
                    document.metadata['title'] = document.page_content
                parent_dict[element_id] = document # 将当前document添加到字典中
            if category != 'Title' and parent_id: # 将其内容追加到对应父文档中
                parent_dict[parent_id].page_content = parent_dict[parent_id].page_content + ' ' + document.page_content
                parent_dict[parent_id].metadata['category'] = 'content'

        # 处理字典
        if parent_dict is not None:
            merged_data.extend(parent_dict.values())

        return merged_data


if __name__ == '__main__':
    file_path = r'..\data\md\overview.md'
    parser = MarkdownParser()
    docs = parser.parse_markdown_to_documents(file_path)
    for item in docs:
        print(f"元数据: {item.metadata}")
        print(f"标题: {item.metadata.get('title', None)}")
        print(f"doc的内容: {item.page_content}\n")
        print("------" * 10)
