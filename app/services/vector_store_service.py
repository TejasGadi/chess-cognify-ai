"""
Vector store service for managing Qdrant collections and document embeddings.
"""
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_qdrant import QdrantVectorStore
from app.config import settings
from app.utils.embeddings import get_embeddings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """Service for managing Qdrant vector store operations."""

    def __init__(self):
        """Initialize vector store service."""
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
        self.embeddings = get_embeddings()
        self.collection_name = settings.qdrant_collection_name

    def initialize_collection(self, force_recreate: bool = False) -> None:
        """
        Initialize or recreate Qdrant collection.

        Args:
            force_recreate: If True, delete existing collection and create new one
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(
                c.name == self.collection_name for c in collections
            )

            if collection_exists:
                if force_recreate:
                    logger.warning(f"Deleting existing collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return

            # Get embedding dimensions (bge-m3 has 1024 dimensions)
            # We'll use a test embedding to get dimensions
            test_embedding = self.embeddings.embed_query("test")
            vector_size = len(test_embedding)

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                f"Created Qdrant collection: {self.collection_name} "
                f"(dimensions: {vector_size})"
            )

        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")
            raise

    def get_vector_store(self) -> QdrantVectorStore:
        """
        Get LangChain QdrantVectorStore instance.

        Returns:
            QdrantVectorStore instance
        """
        return QdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )

    def add_documents(
        self, chunks: List[Dict[str, str]], book_id: str
    ) -> List[str]:
        """
        Add document chunks to vector store.

        Args:
            chunks: List of chunk dictionaries with 'text' and 'metadata'
            book_id: Book ID for filtering

        Returns:
            List of document IDs created
        """
        try:
            vector_store = self.get_vector_store()

            # Prepare documents for LangChain
            documents = []
            ids = []

            for idx, chunk in enumerate(chunks):
                doc_id = f"{book_id}_chunk_{chunk['metadata']['chunk_index']}"
                ids.append(doc_id)

                # Create document with metadata
                from langchain_core.documents import Document

                doc = Document(
                    page_content=chunk["text"],
                    metadata={
                        **chunk["metadata"],
                        "book_id": book_id,
                        "doc_id": doc_id,
                    },
                )
                documents.append(doc)

            # Add to vector store
            vector_store.add_documents(documents, ids=ids)
            logger.info(f"Added {len(documents)} chunks to vector store for book {book_id}")

            return ids

        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")
            raise

    def search(
        self, query: str, book_id: Optional[str] = None, top_k: int = 5
    ) -> List[Dict]:
        """
        Search for similar documents in vector store.

        Args:
            query: Search query text
            book_id: Optional book ID to filter results
            top_k: Number of results to return

        Returns:
            List of search results with 'text', 'metadata', and 'score'
        """
        try:
            vector_store = self.get_vector_store()

            # Build filter if book_id provided
            filter_dict = None
            if book_id:
                # Use metadata filter dict format for LangChain
                filter_dict = {"book_id": book_id}

            # Perform similarity search
            results = vector_store.similarity_search_with_score(
                query, k=top_k, filter=filter_dict
            )

            # Format results
            formatted_results = []
            for doc, score in results:
                formatted_results.append(
                    {
                        "text": doc.page_content,
                        "metadata": doc.metadata,
                        "score": float(score),
                    }
                )

            logger.debug(
                f"Found {len(formatted_results)} results for query: {query[:50]}..."
            )
            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            raise

    def delete_book_documents(self, book_id: str) -> int:
        """
        Delete all documents for a specific book.

        Args:
            book_id: Book ID to delete

        Returns:
            Number of documents deleted
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Search for all documents with this book_id using Qdrant client directly
            # First, get all points with this book_id
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="book_id",
                        match=MatchValue(value=book_id),
                    )
                ]
            )

            # Scroll through all points with this filter
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=10000,
                with_payload=True,
            )

            if points:
                # Extract point IDs
                point_ids = [point.id for point in points]

                # Delete points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids,
                )
                logger.info(f"Deleted {len(point_ids)} documents for book {book_id}")
                return len(point_ids)
            else:
                logger.info(f"No documents found for book {book_id}")
                return 0

        except Exception as e:
            logger.error(f"Error deleting documents for book {book_id}: {e}")
            raise
