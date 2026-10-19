from langchain_ollama import OllamaEmbeddings  # <-- UPDATED!
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os

class RAGService:
    def __init__(self, persist_directory: str = "chroma_data"):
        self.persist_directory = persist_directory

        # Initialize embedding model using local Ollama Mistral
        self.embedding = OllamaEmbeddings(model="mistral")

        # Load or create vector store
        if os.path.exists(os.path.join(persist_directory, "index")):
            self.vectordb = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.embedding,
            )
        else:
            self.vectordb = self._create_vectorstore()

    def _create_vectorstore(self):
        # Load all .txt files in /legal_docs/
        all_docs = []
        doc_dir = "legal_docs"
        print("legal_docs dir exists?", os.path.exists(doc_dir))
        print("Files in legal_docs:", os.listdir(doc_dir))
        for filename in os.listdir(doc_dir):
            if filename.endswith(".txt"):
                path = os.path.join(doc_dir, filename)
                print("Loading:", path)
                loader = TextLoader(path, encoding="utf-8")
                docs = loader.load()
                all_docs.extend(docs)

        # Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunked_docs = splitter.split_documents(all_docs)
        if not chunked_docs:
            raise RuntimeError("No documents found to index! Put some .txt files in 'legal_docs' directory.")

        print("Number of chunked_docs:", len(chunked_docs))
        for doc in chunked_docs[:3]:
            print(doc)

        # Create vector store
        vectordb = Chroma.from_documents(
            documents=chunked_docs,
            embedding=self.embedding,  # Use 'embedding', not 'embedding_function'
            persist_directory=self.persist_directory,
        )
        vectordb.persist()
        return vectordb

    def retrieve_context(self, query: str, k: int = 4) -> str:
        results: list[Document] = self.vectordb.similarity_search(query, k=k)
        return "\n\n".join(doc.page_content for doc in results)
