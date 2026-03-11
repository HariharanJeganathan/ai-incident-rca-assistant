import json
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "incidents.json"


class RAGPipeline:

    def __init__(self):

        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        self.vector_store = None

    def load_incidents(self):

        with open(DATA_PATH, "r") as f:
            incidents = json.load(f)

        documents = []

        for incident in incidents:

            text = f"""
            Incident Title: {incident['title']}
            Service: {incident['service']}
            Error Logs: {incident['error_logs']}
            Root Cause: {incident['root_cause']}
            Resolution: {incident['resolution']}
            """

            documents.append(Document(page_content=text))

        return documents

    def build_vector_store(self):

        docs = self.load_incidents()

        self.vector_store = FAISS.from_documents(
            docs,
            self.embeddings
        )

    def retrieve_similar_incidents(self, query, k=3):

        results = self.vector_store.similarity_search(query, k=k)

        return [r.page_content for r in results]