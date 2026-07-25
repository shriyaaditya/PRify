import uuid
from typing import List

from langchain_text_splitters import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.rag.loaders.repository_loader import DiscoveredDocument
from app.rag.models import DocumentChunk, DocumentMetadata


class TextChunker:
    """
    Splits documents into semantically meaningful chunks while preserving headers.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
        )

    def chunk_documents(
        self, repository: str, docs: List[DiscoveredDocument]
    ) -> List[DocumentChunk]:
        """
        Takes a list of DiscoveredDocuments and returns a list of DocumentChunks.
        """
        chunks = []
        for doc in docs:
            # Decide splitter based on extension
            if doc.path.lower().endswith(".md") or doc.document_type in (
                "README",
                "CONTRIBUTING",
                "ARCHITECTURE",
            ):
                splits = self.markdown_splitter.split_text(doc.content)
            else:
                splits = self.text_splitter.split_text(doc.content)

            # Try parsing AST symbols using ParserManager if it's a source code or test file
            parsed_file = None
            if doc.document_type in ("SOURCE_CODE", "TEST_FILE"):
                try:
                    from app.parsers.tree_sitter.manager import parser_manager

                    parsed_file = parser_manager.parse_file(doc.path, doc.content)
                except Exception:
                    parsed_file = None

            for i, split_content in enumerate(splits):
                chunk_id = str(uuid.uuid4())

                # Attempt to extract section name or symbol
                section = None
                if doc.path.lower().endswith(".md"):
                    lines = split_content.splitlines()
                    for line in lines:
                        if line.startswith("#"):
                            section = line.lstrip("# ").strip()
                            break

                # Match symbols in parsed_file if available
                matching_symbols = []
                if parsed_file and parsed_file.symbols:
                    for sym in parsed_file.symbols:
                        if sym.name and sym.name in split_content:
                            matching_symbols.append(f"{sym.kind}:{sym.name}")

                symbol_name = matching_symbols[0] if matching_symbols else None

                metadata = DocumentMetadata(
                    repository=repository,
                    document=doc.path.split("/")[-1],
                    path=doc.path,
                    document_type=doc.document_type,
                    chunk_id=chunk_id,
                    checksum=doc.checksum,
                    section=section or symbol_name,
                )

                chunks.append(
                    DocumentChunk(id=chunk_id, content=split_content, metadata=metadata)
                )

        return chunks
