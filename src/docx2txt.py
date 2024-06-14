# 必要なライブラリのインストール
from typing import List

import chainlit as cl
import nltk
from chainlit.input_widget import Select, Slider, Switch
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import PyMuPDFLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from langchain.schema.runnable import Runnable
from langchain.schema.runnable.config import RunnableConfig
from langchain.text_splitter import SpacyTextSplitter
from langchain_community.document_loaders import (
    UnstructuredExcelLoader, UnstructuredWordDocumentLoader)
from langchain_community.vectorstores import Annoy
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

nltk.download('punkt')

# 環境変数の読み込み
import config

openai_client_key = config.OPENAI_API_KEY
chainlit_outh_key = config.CHAINLIT_AUTH_SECRET
    

#思考の可視化
@cl.step
async def tool():
    # Simulate a running task
    await cl.sleep(2)

    return "Response from the tool!"


@cl.on_settings_update
async def setup_llm(settings):
    llm = ChatOpenAI(
        temperature=settings["Temperature"],
        streaming=settings["Streaming"],
        model=settings["Model"],
    )
    llm.model_name = settings["Model"]  
    cl.user_session.set("llm", llm)
    cl.user_session.set("llm.model_name", llm.model_name)
    await cl.Message(content=f"{llm.model_name}が選択されています。").send()
    
    #会話の途中で設定を変えたらまた最初から
    actions = [
        cl.Action(name="ファイルについて会話", value="value1", description="ファイルについて会話"),
        cl.Action(name="外国人女の子との会話", value="value2", description="普通の会話")
    ]

    await cl.Message(content="好きなものを選択してください！:", actions=actions).send()


#llmの設定画面
@cl.on_chat_start  
async def on_chat_start():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"],
                initial_index=0,
            ),
            Switch(id="Streaming", label="OpenAI - Stream Tokens", initial=True),
            Slider(
                id="Temperature",
                label="OpenAI - Temperature",
                initial=1,
                min=0,
                max=2,
                step=0.1,
            )
        ]
    ).send()

    actions = [
        cl.Action(name="ファイルについて会話", value="value1", description="ファイルについて会話"),
        cl.Action(name="外国人女の子との会話", value="value2", description="普通の会話")
    ]

    await cl.Message(content="好きなものを選択してください！:", actions=actions).send()
    cl.user_session.set("settings", settings)
    await setup_llm(settings)  #初期値のllm


#nomal_chatボタンが押されたら会話画面に移動
@cl.action_callback("外国人女の子との会話")
async def on_chat_action(action):

    '''
    ２つの選択ボタンを閉じたい。
    
    '''

    llm = cl.user_session.get("llm")
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "あなたは北欧からの留学生で性別は女性。年齢は19才です。ユーザーからの質問に対して、かわいく少しカタコトな日本語で、答えてください。たまに、ユーザーをねぇ、と呼んでください。日本語の文法をよく間違えます。",
            ),
            ("human", "{question}"),
        ]
    )

    runnable = prompt | llm | StrOutputParser()
    cl.user_session.set("runnable", runnable)
    file = None
    cl.user_session.set("file",file)


#select_fileボタンが押されたらファイル選択画面に移動
@cl.action_callback("ファイルについて会話")
async def on_file_action(action):

    #履歴を初期化
    message_history = ChatMessageHistory()
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        chat_memory=message_history,
        return_messages=True,
    )

    # ファイルを読み込む
    files = None
    while files is None:
        files = await cl.AskFileMessage(
            max_size_mb=20,
            content=".pdf/.docx/.xlsxに対応してます！",
            accept=["application/pdf" , "application/vnd.openxmlformats-officedocument.wordprocessingml.document" , "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
            raise_on_timeout=False,
        ).send()
    file = files[0]
    file_extension = file.path.split('.')[-1]

    if file_extension == 'docx':
        documents = UnstructuredWordDocumentLoader(file.path).load()
    elif file_extension == 'xlsx':
        documents = UnstructuredExcelLoader(file.path).load()
    elif file_extension == 'pdf':
        documents = PyMuPDFLoader(file.path).load()
    else:
        raise ValueError("Unsupported file type")

    # documentの分割
    text_splitter = SpacyTextSplitter(chunk_size=400, pipeline="ja_core_news_sm")
    splitted_documents = text_splitter.split_documents(documents)

    # ベクトルストアの作成
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    database = Annoy.from_documents(splitted_documents, embeddings)

    #chainの作成
    llm = cl.user_session.get("llm")
    chain = ConversationalRetrievalChain.from_llm(
        llm = llm,
        chain_type="stuff",
        retriever=database.as_retriever(),
        memory=memory,
        return_source_documents=True
    )
    cl.user_session.set("chain", chain)
    cl.user_session.set("file",file)

    llm.model_name = cl.user_session.get("llm.model_name")
    await cl.Message(content=f"{llm.model_name}が選択されています。").send()

    if file_extension == 'docx':
        content=".docxファイルを読み込みました。何でも質問してね！"
    elif file_extension == 'xlsx':
        content=".xlsxファイルを読み込みました。何でも質問してね！"
    elif file_extension == 'pdf':
        content=".pdfファイルを読み込みました。何でも質問してね！"
    
    await cl.Message(content=content).send()
    



@cl.on_message
async def on_message(message: cl.Message):
    file = cl.user_session.get("file")
    if file:
        # chainを元に、openaiから回答を受け取り、ソースとともに表示
        tool_res = await tool()
        chain = cl.user_session.get("chain")
        cb = cl.AsyncLangchainCallbackHandler()

        res = await chain.ainvoke(message.content, callbacks=[cb])
        answer = res["answer"]
        source_documents = res["source_documents"]

        text_elements = []
        if source_documents:
            for source_idx, source_doc in enumerate(source_documents):
                source_name = f"source_{source_idx}"
                text_elements.append(
                    cl.Text(content=source_doc.page_content, name=source_name)
                )
            
            source_names = [text_el.name for text_el in text_elements]

            if source_names:
                answer += f"\nSources: {', '.join(source_names)}"
            else:
                answer += "\nNo sources found"

        await cl.Message(content=answer, elements=text_elements).send()
    
    else:
        runnable = cl.user_session.get("runnable")  # type: Runnable
        msg = cl.Message(content="")
        async for chunk in runnable.astream(
            {"question": message.content},
            config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
        ):
            await msg.stream_token(chunk)

        await msg.send()

