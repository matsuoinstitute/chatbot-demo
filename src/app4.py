from langchain.chat_models import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.document_loaders import PyMuPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQAWithSourcesChain

import chainlit as cl
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

    file = file[0] if isinstance(file, list) else file
    ext = os.path.splitext(file.path)[1]
    if ext == ".pdf":
        text = PyMuPDFLoader(file.path).load()
    elif ext == ".docx":
        text = Docx2txtLoader(file.path).load()
    elif ext == ".xlsx":
        text = UnstructuredExcelLoader(file.path).load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    documents = text_splitter.split_documents(text)
    for i in range(len(documents)):
        documents[i].metadata["source"] = f"source_{i}"
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    db = Chroma.from_documents(documents, embeddings)

    qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
        ChatOpenAI(model=MODEL_NAME, temperature=0),
        chain_type="stuff",
        retriever=db.as_retriever(),
        return_source_documents=True,
        verbose=True
    )

    cl.user_session.set("chain", qa_chain)
    file_name = file[0].name if isinstance(file, list) else file.name
    await cl.Message(content=f"`{file_name}` の準備が完了しました！").send()
    return qa_chain

@cl.on_message
async def process_response(res: cl.Message):
    chain = cl.user_session.get("chain")
    ans = await chain.acall(res.content)
    answer = ans['answer']
    sources = ans["sources"].strip().split(',')
    source_elements = [cl.Text(content=str(ans['source_documents'][s].page_content), name="source_" + str(s)) for s in range(len(sources))]
    source_names = [source_el.name for source_el in source_elements]
    answer += f"\n参照元: {', '.join(source_names)}"
    await cl.Message(content=answer, elements=source_elements).send()