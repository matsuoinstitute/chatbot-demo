from langchain.document_loaders import (Docx2txtLoader, PyMuPDFLoader,
                                        UnstructuredExcelLoader)


def pdf_loader(file_path):
    documents = PyMuPDFLoader(file_path).load()
    return documents


def word_loader(file_path):
    documents = Docx2txtLoader(file_path).load()
    return documents


def excel_loader(file_path):
    documents = UnstructuredExcelLoader(file_path, mode="elements").load()
    return documents
