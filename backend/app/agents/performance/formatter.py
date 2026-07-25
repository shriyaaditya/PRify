import re

from app.agents.base.context import ReviewContext


class PerformanceContextFormatter:
    """
    Formats the ReviewContext into a token-efficient string tailored for performance and scalability analysis.
    Prioritizes code containing loops, database queries, collection operations, async/blocking patterns,
    Tree-sitter AST symbols, and performance guidelines from RAG.
    """

    PERFORMANCE_KEYWORDS_PATTERN = re.compile(
        r"\b(for|while|loop|select|query|fetch|execute|find|orm|http|axios|requests|map|filter|reduce|sort|await|sleep|sync|read|write|cache)\b",
        re.IGNORECASE,
    )

    @classmethod
    def is_performance_relevant(cls, filename: str, patch: str = "") -> bool:
        """
        Internal heuristic used ONLY for prompt diff ordering/prioritization.
        This helper is never emitted or used as a performance finding itself.
        """
        combined = filename + " " + patch
        return bool(cls.PERFORMANCE_KEYWORDS_PATTERN.search(combined))

    @classmethod
    def format_for_performance(
        cls,
        context: ReviewContext,
        max_files: int = 10,
        max_symbols: int = 30,
        max_docs_chars: int = 4000,
    ) -> str:
        formatted_parts = []

        # 1. PR Metadata
        formatted_parts.append("### [Source: GitHub PR Metadata] Pull Request Context")
        formatted_parts.append(f"Title: {context.pull_request.title}")
        if context.pull_request.description:
            formatted_parts.append(f"Description: {context.pull_request.description}")

        # 2. Changed Files (Sorted so performance-sensitive files are ordered first, without excluding any)
        formatted_parts.append("\n### [Source: GitHub Diff] Changed Code")
        sorted_files = sorted(
            context.changed_files,
            key=lambda cf: (
                0
                if cls.is_performance_relevant(
                    cf.filename, getattr(cf, "patch", "") or ""
                )
                else 1
            ),
        )

        for cf in sorted_files[:max_files]:
            status_str = getattr(cf, "status", "modified")
            formatted_parts.append(
                f"--- File: {cf.filename} (Status: {status_str}) ---"
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

        # 4. Retrieved Performance Documentation
        if context.retrieved_context:
            formatted_parts.append(
                "\n### [Source: Qdrant Vector DB] Repository Performance Guidelines & Documentation"
            )
            docs_text = ""
            for doc in context.retrieved_context:
                if isinstance(doc, dict):
                    content = doc.get("page_content", str(doc))
                    source = doc.get("metadata", {}).get(
                        "source", "Performance Guideline"
                    )
                    docs_text += f"[Document: {source}]\n{content}\n\n"
                elif hasattr(doc, "page_content"):
                    source = getattr(doc, "metadata", {}).get(
                        "source", "Performance Guideline"
                    )
                    docs_text += f"[Document: {source}]\n{doc.page_content}\n\n"
                else:
                    docs_text += f"{str(doc)}\n\n"

            if len(docs_text) > max_docs_chars:
                docs_text = (
                    docs_text[:max_docs_chars]
                    + "\n...[truncated due to context budget]"
                )

            formatted_parts.append(docs_text)

        return "\n".join(formatted_parts)
