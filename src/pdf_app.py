import os

import chainlit as cl
from dotenv import load_dotenv
from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

from document_loader import excel_loader, pdf_loader, word_loader

load_dotenv("../.env")

ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
]

ALLOWED_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".xlsx",
]

prompt = PromptTemplate(
    template="""
    文章を前提にして質問に答えてください。

    文章 :
    {document}

    質問 : {question}
    """,
    input_variables=["document", "question"],
)


@cl.on_chat_start
async def on_chat_start():
    """初回起動時に呼び出される."""
    files = None

    # awaitメソッドのために、whileを利用する。アップロードされるまで続く。
    while files is None:
        # chainlitの機能に、ファイルをアップロードさせるメソッドがある。
        files = await cl.AskFileMessage(
            # ファイルの最大サイズ
            max_size_mb=20,
            # ファイルをアップロードさせる画面のメッセージ
            content="ファイルを選択してください（.pdf、.docx、.xlsxに対応しています）",
            # PDFファイルを指定する
            accept=ALLOWED_MIME_TYPES,
            # タイムアウトなし
            raise_on_timeout=False,
        ).send()

    file = files[0]
    ext = os.path.splitext(file.name)[1]

    # アップロードされたファイルのパスから中身を読み込む。
    if ext in ALLOWED_EXTENSIONS:
        if ext == ".pdf":
            documents = pdf_loader(file.path)
        elif ext == ".docx":
            documents = word_loader(file.path)
        else:
            documents = excel_loader(file.path)

        text_splitter = CharacterTextSplitter(chunk_size=500)
        splitted_documents = text_splitter.split_documents(documents)

        # テキストをベクトル化するOpenAIのモデル
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

        # Chromaにembedding APIを指定して、初期化する。
        database = Chroma(embedding_function=embeddings)

        # PDFから内容を分割されたドキュメントを保存する。
        database.add_documents(splitted_documents)

        # 今回は、簡易化のためセッションに保存する。
        cl.user_session.set("data", database)
        await cl.Message(content="アップロードが完了しました！").send()
    
    llm = ChatOpenAI(model="gpt-4-0125-preview", temperature=0)
    message_history = ChatMessageHistory()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        chat_memory=message_history,
        return_messages=True,
    )

    if database is not None:
        retriever = database.as_retriever()
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            verbose=True,
            memory=memory,
            return_source_documents=True,
        )
        cl.user_session.set("qa", qa)


@cl.on_message
async def on_message(input_message: cl.Message):
    """メッセージが送られるたびに呼び出される."""
    qa = cl.user_session.get("qa")

    res = await qa.acall(
        input_message.content,
        callbacks=[cl.AsyncLangchainCallbackHandler()]
    )
    answer = res["answer"]
    source_documents = res["source_documents"]
    text_elements = []

    if source_documents:
        for source_idx, source_doc in enumerate(source_documents):
            source_name = f"source_{source_idx}"
            # Create the text element referenced in the message
            text_elements.append(
                cl.Text(content=source_doc.page_content, name=source_name)
            )
        source_names = [text_el.name for text_el in text_elements]

        if source_names:
            answer += f"\n参照元: {', '.join(source_names)}"
        else:
            answer += "\n参照先が見つかりませんでした。"

    await cl.Message(content=answer, elements=text_elements).send()
