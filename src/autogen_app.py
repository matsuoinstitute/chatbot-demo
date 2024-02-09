import os

import autogen
import chainlit as cl
from dotenv import find_dotenv, load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma

from agents.chainlit_agents import (ChainlitAssistantAgent,
                                    ChainlitUserProxyAgent)
from document_loader import excel_loader, pdf_loader, word_loader
from initiate_chat import initiate_chat
from prompt import get_assistant_prompt, get_manager_prompt

load_dotenv(find_dotenv())

USER_PROXY_NAME = "Query Agent"
ASSISTANT = "Assistant"

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

config_list = autogen.config_list_from_dotenv(
    dotenv_file_path = '.env',
    model_api_key_map={
        "gpt-3.5-turbo-1106": "OPENAI_API_KEY",
    },
    filter_dict={
        "model": {
            "gpt-3.5-turbo-1106",
        }
    }
)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
llm_config = {"config_list": config_list, "api_key": OPENAI_API_KEY, "cache_seed": 42}


@cl.on_chat_start
async def on_chat_start():
    try:
        assistant = ChainlitAssistantAgent(
            name="Assistant", llm_config=llm_config,
            system_message=get_assistant_prompt(),
            description="Assistant Agent"
        )

        user_proxy = ChainlitUserProxyAgent(
            name="User_Proxy",
            human_input_mode="ALWAYS",
            llm_config=llm_config,
            # max_consecutive_auto_reply=3,
            # is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config=False,
            system_message=get_manager_prompt(),
            description="User Proxy Agent"
        )
        print("Set agents.")

        cl.user_session.set(USER_PROXY_NAME, user_proxy)
        cl.user_session.set(ASSISTANT, assistant)

        msg = cl.Message(content="""こんにちは！何をお手伝いしましょう。""", author="User_Proxy")
        await msg.send()

        print("Message sent.")

    except Exception as e:
        print("Error: ", e)
        pass

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

        text_splitter = CharacterTextSplitter(chunk_size=400)
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


@cl.on_message
async def run_conversation(message: cl.Message):
    print("Running conversation")
    llm_config = {"config_list": config_list, "api_key": OPENAI_API_KEY, "cache_seed": 42}

    CONTEXT = message.content
    MAX_ITER = 10
    assistant = cl.user_session.get(ASSISTANT)
    user_proxy = cl.user_session.get(USER_PROXY_NAME)
    database = cl.user_session.get("data")
    # 質問された文から似た文字列を、DBより抽出
    documents = database.similarity_search(message.content)

    # 抽出したものを結合
    documents_string = ""
    for document in documents:
        documents_string += f"""
        ---------------------------------------------
        {document.page_content}
        """
    print("Setting grouipchat")
    groupchat = autogen.GroupChat(agents=[user_proxy, assistant], messages=[], max_round=MAX_ITER)
    manager = autogen.GroupChatManager(groupchat=groupchat,llm_config=llm_config)

# -------------------- Conversation Logic. Edit to change your first message based on the Task you want to get done. ----------------------------- # 
    if len(groupchat.messages) == 0:
        message = f"""Do the task based on the user input: {CONTEXT}.\n\nDocument:{documents_string}"""
        # user_proxy.initiate_chat(manager, message=message)
        await cl.Message(content=f"""Starting agents on task...""").send()
        await cl.make_async(user_proxy.initiate_chat(manager, message=initiate_chat(message), config_list=config_list))( manager, message=message, )
    elif len(groupchat.messages) < MAX_ITER:
        await cl.make_async(user_proxy.send)( manager, message=CONTEXT, )
    elif len(groupchat.messages) == MAX_ITER:  
        await cl.make_async(user_proxy.send)( manager, message="exit", )