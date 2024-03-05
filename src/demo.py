import os

import chainlit as cl
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

from document_loader import excel_loader, pdf_loader, word_loader

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
あなたは優秀なQAシステムです。アップロードされたファイルの文章が与えられます。以下の注意点を考慮して、ユーザーからの質問に回答してください。
# 注意点:
- ユーザーが「PDF」「エクセル」などと言うときは、以下の「文章」を指しています。
- 「文章」に記載の情報を元に回答するようにし、記載のない情報については回答できない旨を伝えてください。
# 文章:
{document}
# 質問:
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
            content="ファイルを選択してください（.pdf、.docx、.xlsxに対応しています）",
            accept=ALLOWED_MIME_TYPES,
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

        # ページごとに分割されている文章を統合し、トークン数制限の関係から指定した文字数までに切り捨てる。
        documents_content = ""
        for document in documents:
            documents_content += document.page_content
        cl.user_session.set("documents", documents_content[:5000])

        await cl.Message(content="アップロードが完了しました！").send()
    else:
        await cl.Message(content="アップロードされたファイルは対応していません。").send()


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