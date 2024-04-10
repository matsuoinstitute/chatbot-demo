from langchain.chat_models import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain

import chainlit as cl
import shutil
import openai
import os

DB_PATH = './.chroma'
CHUNK_SIZE = 500
CHUNK_OVERLAP = 10
MODEL_NAME = "gpt-4"

@cl.on_chat_start
async def init():
    file = None
    while file is None:
        file = await cl.AskFileMessage(content="PDF, DOCX, XLSXファイルをアップロードしてください！", accept=[".pdf", ".docx", ".xlsx"]).send()
    # データベースの初期化
    #shutil.rmtree(DB_PATH, ignore_errors=True)
    # ファイルからテキストを抽出し、データベースを作成
    file = file[0] if isinstance(file, list) else file
    print(file)
    print(type(file))
    ext = os.path.splitext(file.path)[1]
    if ext == ".pdf":
        text = PyMuPDFLoader(file.path).load()
    elif ext == ".docx":
        text = Docx2txtLoader(file.path).load()
    elif ext == ".xlsx":
        text = UnstructuredExcelLoader(file.path).load()

    text_splitter = CharacterTextSplitter(chunk_size=CHUNK_SIZE)
    documents = text_splitter.split_documents(text)
    for i in range(0, len(documents)):
        documents[i].metadata["source"] = f"source_{i}"
    metadatas = [f"source_{i}" for i in range(0, len(documents))]
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    db = Chroma.from_documents(documents, embeddings, metadatas)
    #db = Chroma(embedding_function=embeddings)  #https://qiita.com/lighlighlighlighlight/items/a7fe1224fa1d904a4426
    #db.add_documents(documents)

    chain = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI(model=MODEL_NAME, temperature=0),
        chain_type="stuff",
        retriever=db.as_retriever(),
    )
    # テキストをユーザーセッションに保存
    cl.user_session.set("chain", chain)
    file_name = file[0].name if isinstance(file, list) else file.name
    await cl.Message(content=f"`{file_name}` の準備が完了しました！").send()
    return chain


@cl.on_message
async def process_response(res: cl.Message):
    chain = cl.user_session.get("chain")
    ans = await chain.acall(res.content)
    sources = ans["sources"].strip().split(',')
    source_elements = [cl.Text(content=ans['sources'][s], name="page_" + str(s)) for s in range(len(sources))]
    response = f"{ans['answer']} 出典: {ans['sources']}"
    await cl.Message(content=response, elements=source_elements).send()

"""async def process_pdf(file):
    file = file[0] if isinstance(file, list) else file
    reader = PyMuPDFLoader(file.path).load()
    return reader

# テキストを分割し、埋め込みを作成してデータベースを作成する関数
async def create_db(text):
    text_splitter = CharacterTextSplitter(chunk_size=CHUNK_SIZE)
    documents = text_splitter.split_documents(text)
    #for i, text in enumerate(docs):
    #    docs.metadata["source"] = f"{i}-pl"
    #metadatas = [{"source": f"{i}-pl"} for i in range(len(docs))]
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    #db = Chroma.from_documents(docs, embeddings)
    db = Chroma(embedding_function=embeddings)  #https://qiita.com/lighlighlighlighlight/items/a7fe1224fa1d904a4426
    db = Chroma.add_documents(documents=documents)
    return db, docs"""