import os
from typing import List
from langchain_openai import OpenAIEmbeddings

class EmbeddingService:
    """
    Abstractions around embedding generation.
    Supports future expansion to local models or other cloud providers.
    """
    def __init__(self, model_name: str = "text-embedding-3-small"):
        # Relies on OPENAI_API_KEY being present in environment
        self._embedder = OpenAIEmbeddings(model=model_name)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Asynchronously embed a list of texts.
        """
        return await self._embedder.aembed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """
        Asynchronously embed a single query text.
        """
        return await self._embedder.aembed_query(text)

    def get_langchain_embedder(self) -> OpenAIEmbeddings:
        """
        Returns the underlying langchain embedder (useful for integrating with LangChain vector stores).
        """
        return self._embedder
