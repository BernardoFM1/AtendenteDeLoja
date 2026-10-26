import os
import shutil
from typing import List

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import RAG_FILES_DIR, VECTOR_STORE_PATH

def load_documents() -> List[Document]:
    """Varre o diretório RAG em busca de arquivos PDF/TXT, carrega e move para processed/."""
    docs: List[Document] = []
    processed_dir = os.path.join(RAG_FILES_DIR, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    if not os.path.exists(RAG_FILES_DIR):
        os.makedirs(RAG_FILES_DIR, exist_ok=True)
        return docs

    files = [
        os.path.join(RAG_FILES_DIR, f)
        for f in os.listdir(RAG_FILES_DIR)
        if (f.endswith(".pdf") or f.endswith(".txt")) and os.path.isfile(os.path.join(RAG_FILES_DIR, f))
    ]

    for file in files:
        loader = PyPDFLoader(file) if file.endswith(".pdf") else TextLoader(file)
        docs.extend(loader.load())
        dest_path = os.path.join(processed_dir, os.path.basename(file))
        shutil.move(file, dest_path)

    return docs

def get_vectorstore() -> Chroma:
    """Inicializa ou recupera o banco vetorial Chroma com os documentos processados."""
    docs = load_documents()
    if docs:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        splits = text_splitter.split_documents(docs)
        return Chroma.from_documents(
            documents=splits,
            embedding=OpenAIEmbeddings(),
            persist_directory=VECTOR_STORE_PATH,
        )

    return Chroma(
        embedding_function=OpenAIEmbeddings(),
        persist_directory=VECTOR_STORE_PATH,
    )
