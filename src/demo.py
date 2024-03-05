import chainlit as cl
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import PyMuPDFLoader
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage


prompt = PromptTemplate(
    template="""
文章を前提にして質問に答えてください。
文章 :
{document}
質問 :
{question}
""",
    input_variables=["document", "question"],
)


@cl.on_chat_start
async def on_chat_start():
    """初回起動時に呼び出される."""
    files = None

    # awaitメソッドのために、whileを利用する。アップロードされるまで続く。
    while files is None:
        files = await cl.AskFileMessage(
            max_size_mb=20,
            content="PDFを選択してください。",
            accept=["application/pdf"],
            raise_on_timeout=False,
        ).send()

    file = files[0]
    # アップロードされたファイルのパスから中身を読み込む。
    documents = PyMuPDFLoader(file.path).load()

    # ページごとに分割されている文章を統合し、トークン数制限の関係から指定した文字数までに切り捨てる。
    documents_content = ""
    for document in documents:
        documents_content += document.page_content
    cl.user_session.set("documents", documents_content[:5000])

    await cl.Message(content="アップロードが完了しました！").send()


@cl.on_message
async def on_message(input_message: cl.Message):
    """メッセージが送られるたびに呼び出される."""

    # チャット用のOpenAIのモデル
    open_ai = ChatOpenAI(model="gpt-4-0125-preview")

    # ユーザーのセッションに保存されたドキュメントを取得
    documents = cl.user_session.get("documents")

    # プロンプトに埋め込みながらOpenAIに送信
    result = open_ai(
        [
            HumanMessage(
                content=prompt.format(
                    document=documents,
                    question=input_message.content,
                )
            )
        ]
    ).content

    # 下記で結果を表示する(content=をOpenAIの結果にする。)
    await cl.Message(content=result).send()