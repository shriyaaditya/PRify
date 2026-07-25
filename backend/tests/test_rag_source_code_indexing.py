import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.chunking.text_chunker import TextChunker
from app.rag.indexing.indexer import Indexer
from app.rag.loaders.repository_loader import DiscoveredDocument, RepositoryLoader
from app.rag.models import DocumentMetadata, RetrievedContext
from app.rag.retrieval.retriever import Retriever

# --- Test A: Production source discovery ---


def test_production_source_discovery_supported_files():
    loader = RepositoryLoader(gh_client=MagicMock(), repo_fullname="owner/repo")

    assert loader._is_supported_file("src/main.py") is True
    assert loader._is_supported_file("src/services/auth.ts") is True
    assert loader._is_supported_file("frontend/components/Login.tsx") is True
    assert loader._is_supported_file("backend/app/routes.js") is True
    assert loader._is_supported_file("components/Button.jsx") is True

    assert loader._determine_document_type("src/main.py") == "SOURCE_CODE"
    assert loader._determine_document_type("src/services/auth.ts") == "SOURCE_CODE"
    assert (
        loader._determine_document_type("frontend/components/Login.tsx")
        == "SOURCE_CODE"
    )


# --- Test B: Excluded directories and sensitive files ---


def test_excluded_directories_and_sensitive_files():
    loader = RepositoryLoader(gh_client=MagicMock(), repo_fullname="owner/repo")

    # Excluded directories
    assert loader._is_supported_file("node_modules/express/index.js") is False
    assert (
        loader._is_supported_file(".venv/lib/python3.13/site-packages/pydantic/main.py")
        is False
    )
    assert loader._is_supported_file("venv/bin/activate.py") is False
    assert loader._is_supported_file("dist/bundle.js") is False
    assert loader._is_supported_file("build/main.js") is False
    assert loader._is_supported_file(".git/config") is False
    assert loader._is_supported_file(".next/server/pages.js") is False
    assert loader._is_supported_file("coverage/lcov.js") is False
    assert loader._is_supported_file("__pycache__/main.cpython-313.pyc") is False

    # Sensitive files / lockfiles
    assert loader._is_supported_file(".env") is False
    assert loader._is_supported_file(".env.local") is False
    assert loader._is_supported_file(".env.production") is False
    assert loader._is_supported_file("package-lock.json") is False
    assert loader._is_supported_file("poetry.lock") is False


# --- Test C: Documentation remains supported ---


def test_documentation_files_remain_supported():
    loader = RepositoryLoader(gh_client=MagicMock(), repo_fullname="owner/repo")

    assert loader._is_supported_file("README.md") is True
    assert loader._is_supported_file("CONTRIBUTING.md") is True
    assert loader._is_supported_file("docs/architecture.md") is True
    assert loader._is_supported_file("adr/0001-record.md") is True

    assert loader._determine_document_type("README.md") == "README"
    assert loader._determine_document_type("CONTRIBUTING.md") == "CONTRIBUTING"
    assert loader._determine_document_type("docs/architecture.md") == "ARCHITECTURE"


# --- Test D: Metadata & Tree-sitter symbol attachment ---


def test_chunk_metadata_and_symbol_attachment():
    chunker = TextChunker()
    doc = DiscoveredDocument(
        path="app/services/auth_service.py",
        content="class AuthService:\n    def validate_token(self, token: str):\n        return True\n",
        checksum="hash123",
        document_type="SOURCE_CODE",
    )

    chunks = chunker.chunk_documents("owner/repo", [doc])

    assert len(chunks) > 0
    chunk = chunks[0]
    assert chunk.metadata.repository == "owner/repo"
    assert chunk.metadata.path == "app/services/auth_service.py"
    assert chunk.metadata.document == "auth_service.py"
    assert chunk.metadata.document_type == "SOURCE_CODE"
    assert chunk.metadata.checksum == "hash123"
    # Verify symbol extracted from Tree-sitter AST
    assert chunk.metadata.section is not None
    assert (
        "AuthService" in chunk.metadata.section
        or "validate_token" in chunk.metadata.section
    )


# --- Test E: Incremental Indexing ---


@pytest.mark.anyio
async def test_incremental_indexing_skips_unchanged_files():
    mock_gh_client = MagicMock()
    mock_session = AsyncMock()

    # Existing document in DB with checksum 'hash123'
    existing_doc = MagicMock()
    existing_doc.document_name = "app/services/auth_service.py"
    existing_doc.checksum = "hash123"

    mock_db_result = MagicMock()
    mock_db_result.scalars.return_value.all.return_value = [existing_doc]
    mock_session.execute = AsyncMock(return_value=mock_db_result)

    with (
        patch("app.rag.indexing.indexer.EmbeddingService"),
        patch("app.rag.indexing.indexer.RepositoryLoader") as mock_loader_cls,
    ):
        indexer = Indexer(gh_client=mock_gh_client, session=mock_session)
        mock_embed = indexer.embedder.aembed_documents = AsyncMock()
        mock_upsert = indexer.vectorstore.upsert_chunks = AsyncMock()

        mock_loader = AsyncMock()
        mock_loader_cls.return_value = mock_loader
        mock_loader.discover_documents.return_value = [
            DiscoveredDocument(
                path="app/services/auth_service.py",
                content="class AuthService: pass",
                checksum="hash123",  # matches existing checksum
                document_type="SOURCE_CODE",
            )
        ]

        await indexer.index_repository(
            repository_id=uuid.uuid4(), repo_fullname="owner/repo"
        )

        # Verify re-embedding and upsert skipped
        mock_embed.assert_not_called()
        mock_upsert.assert_not_called()


# --- Test F: Retrieval of unchanged source context ---


@pytest.mark.anyio
async def test_retrieval_returns_relevant_unchanged_source_code():
    with patch("app.rag.retrieval.retriever.EmbeddingService"):
        retriever = Retriever()

        dummy_vector = [0.1] * 1536
    mock_context = RetrievedContext(
        content="class AuthService:\n    def validate_token(self, token: str):\n        pass",
        score=0.92,
        metadata=DocumentMetadata(
            repository="owner/repo",
            document="auth_service.py",
            path="app/services/auth_service.py",
            document_type="SOURCE_CODE",
            chunk_id="c1",
            checksum="hash123",
            section="class:AuthService",
        ),
        source_path="app/services/auth_service.py",
    )

    with (
        patch.object(
            retriever.embedder, "aembed_query", AsyncMock(return_value=dummy_vector)
        ),
        patch.object(
            retriever.vectorstore, "search", AsyncMock(return_value=[mock_context])
        ),
    ):
        # PR changed file is app/api/auth.py, querying for token validation
        results = await retriever.retrieve(
            query="validate_token AuthService token validation",
            repo_fullname="owner/repo",
            limit=5,
        )

        assert len(results) == 1
        assert results[0].source_path == "app/services/auth_service.py"
        assert "AuthService" in results[0].content
        assert results[0].metadata.document_type == "SOURCE_CODE"
