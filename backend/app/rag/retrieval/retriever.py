import logging
from typing import List

from app.rag.embeddings.embedding_service import EmbeddingService
from app.rag.vectorstore.qdrant_client import qdrant_store
from app.rag.models import RetrievedContext

logger = logging.getLogger(__name__)

class Retriever:
    """
    Public API for semantic retrieval from the repository knowledge base.
    """
    def __init__(self, collection_name: str = "repository_docs"):
        self.collection_name = collection_name
        self.embedder = EmbeddingService()
        self.vectorstore = qdrant_store

    async def retrieve(self, query: str, repo_fullname: str, limit: int = 5) -> List[RetrievedContext]:
        """
        Retrieves the top K relevant document chunks for a given query in a specific repository.
        """
        logger.info(f"Retrieving context for query: '{query}' in repo: {repo_fullname}")
        try:
            # Generate embedding for the query
            query_vector = await self.embedder.aembed_query(query)
            
            # Search Qdrant
            results = await self.vectorstore.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                repository=repo_fullname,
                limit=limit
            )
            
            return results
        except Exception as e:
            logger.error(f"Retrieval failed for query '{query}': {str(e)}")
            return []
