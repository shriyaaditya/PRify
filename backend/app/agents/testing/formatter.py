import re

from app.agents.base.context import ReviewContext


class TestingContextFormatter:
    """
    Formats the ReviewContext into a token-efficient string tailored for testing review analysis.
    Prioritizes correlation between changed production code, test file diffs, and existing repository test files/guidelines.
    """

    TEST_PATTERNS = re.compile(
        r"(^|/)(tests?|__tests__)/|\btest_|_test\.|(\.test|\.spec)\.(ts|js|py|rb|go|java|cs|cpp|c|rs)$",
        re.IGNORECASE,
    )

    @classmethod
    def is_test_file(cls, filename: str) -> bool:
        """
        Recognizes test naming/location signals for context prioritization.
        Test naming patterns are context-prioritization signals only; files are never excluded based on filenames.
        """
        return bool(cls.TEST_PATTERNS.search(filename))

    @classmethod
    def format_for_testing(
        cls,
        context: ReviewContext,
        max_files: int = 10,
        max_symbols: int = 30,
        max_docs_chars: int = 4000,
    ) -> str:
        formatted_parts = []

        # 1. PR Context
        formatted_parts.append("### [Source: GitHub PR Metadata] Pull Request Context")
        formatted_parts.append(f"Title: {context.pull_request.title}")
        if context.pull_request.description:
            formatted_parts.append(f"Description: {context.pull_request.description}")

        # 2. Changed Files (Sorted so production & test diffs are ordered clearly)
        formatted_parts.append("\n### [Source: GitHub Diff] Changed Code & Test Files")
        # Put production code diffs first, followed by test diffs, or vice versa; preserve all files within budget
        sorted_files = sorted(
            context.changed_files,
            key=lambda cf: 1 if cls.is_test_file(cf.filename) else 0,
        )

        for cf in sorted_files[:max_files]:
            status_str = getattr(cf, "status", "modified")
            file_type_label = (
                "Test File" if cls.is_test_file(cf.filename) else "Production Code"
            )
            formatted_parts.append(
                f"--- File: {cf.filename} (Status: {status_str}, Type: {file_type_label}) ---"
            )
            if hasattr(cf, "patch") and cf.patch:
                patch = (
                    cf.patch[:2500] + "\n...[truncated]"
                    if len(cf.patch) > 2500
                    else cf.patch
                )
                formatted_parts.append(f"Patch:\n```\n{patch}\n```")

        if len(sorted_files) > max_files:
            formatted_parts.append(
                f"... and {len(sorted_files) - max_files} more changed files omitted due to context budget."
            )

        # 3. Tree-Sitter Symbols
        if context.symbol_tables:
            formatted_parts.append(
                "\n### [Source: Tree-sitter AST] Code Symbols & Functions"
            )
            for symbol in context.symbol_tables[:max_symbols]:
                file_path_str = getattr(
                    symbol, "file_path", getattr(symbol, "filepath", "N/A")
                )
                formatted_parts.append(
                    f"- [{symbol.kind}] {symbol.name} (File: {file_path_str})"
                )
            if len(context.symbol_tables) > max_symbols:
                formatted_parts.append(
                    f"... and {len(context.symbol_tables) - max_symbols} more symbols omitted due to budget."
                )

        # 4. Retrieved Test Files & Guidelines from Qdrant Vector DB
        if context.retrieved_context:
            formatted_parts.append(
                "\n### [Source: Qdrant Vector DB] Existing Repository Test Files & Guidelines"
            )
            docs_text = ""
            for doc in context.retrieved_context:
                if isinstance(doc, dict):
                    content = doc.get("content", doc.get("page_content", str(doc)))
                    source = doc.get(
                        "source",
                        doc.get("metadata", {}).get(
                            "source",
                            doc.get("metadata", {}).get("path", "Repository Context"),
                        ),
                    )
                    doc_type = doc.get(
                        "document_type",
                        doc.get("metadata", {}).get("document_type", "OTHER"),
                    )
                    docs_text += (
                        f"[Document: {source} | Type: {doc_type}]\n{content}\n\n"
                    )
                elif hasattr(doc, "page_content") or hasattr(doc, "content"):
                    content = getattr(
                        doc, "content", getattr(doc, "page_content", str(doc))
                    )
                    meta = getattr(doc, "metadata", {})
                    source = (
                        getattr(
                            meta, "source", getattr(meta, "path", "Repository Context")
                        )
                        if hasattr(meta, "source") or hasattr(meta, "path")
                        else meta.get("source", meta.get("path", "Repository Context"))
                        if isinstance(meta, dict)
                        else "Repository Context"
                    )
                    doc_type = (
                        getattr(meta, "document_type", "OTHER")
                        if hasattr(meta, "document_type")
                        else meta.get("document_type", "OTHER")
                        if isinstance(meta, dict)
                        else "OTHER"
                    )
                    docs_text += (
                        f"[Document: {source} | Type: {doc_type}]\n{content}\n\n"
                    )
                else:
                    docs_text += f"{str(doc)}\n\n"

            if len(docs_text) > max_docs_chars:
                docs_text = (
                    docs_text[:max_docs_chars]
                    + "\n...[truncated due to context budget]"
                )

            formatted_parts.append(docs_text)

        return "\n".join(formatted_parts)
