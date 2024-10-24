import os
from typing import List

from dotenv import load_dotenv
from langchain_community.document_loaders import JSONLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chain_callback import ChainCallback
from store.faiss import FAISSStore
load_dotenv()  # 加载 .env 文件

if __name__ == '__main__':
    llm = ChatOpenAI(
        openai_api_key=os.environ.get("ARK_API_KEY"),
        openai_api_base="https://ark.cn-beijing.volces.com/api/v3",
        model_name="ep-20241024122147-th778"
    )

    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    # 创建 ChatPromptTemplate
    system_prompt = """你是中国矿业大学的问答助手。用以下几段检索到的信息回答问题，保持答案简洁。
                     问题：{question}
                     信息：{context}
                     
                     答案："""

    prompt = ChatPromptTemplate.from_template(system_prompt)

    # FAISS 存储路径
    index_file_path = "faiss_index"
    data_file_path = 'data/news.json'

    # 创建 FAISSStore
    vector_store = FAISSStore(embeddings)

    if os.path.exists(index_file_path):
        print("从本地加载 FAISS 索引...")
        vector_store.load(index_file_path)
    else:
        print("本地没有 FAISS 索引，正在创建...")
        loader = JSONLoader(
            file_path=data_file_path,
            jq_schema='.data[]',
            content_key='content',
            metadata_func=lambda record, metadata:
            {**metadata, "source": record.get("url"), "title": record.get("title"), "date": record.get("date")}
        )
        docs = loader.load()
        print("分割文档并添加到索引")
        spliter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        split_docs = spliter.split_documents(docs)
        vector_store.add_documents(split_docs)
        print("保存 FAISS 索引到本地...")
        vector_store.save(index_file_path)

    # 设置检索器
    retriever = vector_store.index.as_retriever(search_kwargs={"k": 3})

    # 文档格式化函数
    def format_docs(doc_list: List[Document]):
        formatted_docs = []
        index = 1
        for doc in doc_list:
            source = doc.metadata.get("source", "未知来源")  # 从 metadata 获取文档的来源
            content_with_citation = f"第{index}篇文章(来源: {source})：\n\n{doc.page_content[:200]}"
            formatted_docs.append(content_with_citation)
        return "\n\n".join(formatted_docs)


    # 创建 RAG chain
    rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
    )

    # 执行问题查询
    response = rag_chain.invoke("赵宏伟什么时候被任命为校长的？前任校长为什么辞职了", config={"callbacks": [ChainCallback()]})
    print(response)
