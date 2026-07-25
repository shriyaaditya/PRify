import re
from typing import List, Dict, Any
from app.agents.base.context import ReviewContext

class SecurityContextFormatter:
    """
    Formats the ReviewContext into a token-efficient string tailored for security analysis.
    Prioritizes security-sensitive code (auth, secrets, middleware, SQL/exec calls), Semgrep static findings,
    Tree-sitter symbols, and security guidelines from RAG.
    """

    SECURITY_KEYWORDS = [
        "auth", "login", "password", "token", "secret", "key", "jwt",
        "sql", "query", "exec", "eval", "upload", "path", "file", "permission"
    ]

    @classmethod
    def is_security_sensitive(cls, filename: str, patch: str = "") -> bool:
        combined = (filename + " " + patch).lower()
        return any(kw in combined for kw in cls.SECURITY_KEYWORDS)

    @classmethod
    def format_for_security(
        cls,
        context: ReviewContext,
        max_files: int = 10,
        max_symbols: int = 30,
        max_semgrep_findings: int = 20,
        max_docs_chars: int = 4000
    ) -> str:
        formatted_parts = []

        # 1. PR Context
        formatted_parts.append("### [Source: GitHub PR Metadata] Pull Request Context")
        formatted_parts.append(f"Title: {context.pull_request.title}")
        if context.pull_request.description:
            formatted_parts.append(f"Description: {context.pull_request.description}")

        # 2. Semgrep Findings (Prioritized for static evidence)
        if context.semgrep_findings:
            formatted_parts.append("\n### [Source: Semgrep Static Analysis] Static Analysis Results")
            for sf in context.semgrep_findings[:max_semgrep_findings]:
                formatted_parts.append(
                    f"- Rule: {sf.rule_id} | File: {sf.file_path}:{sf.line_number} | Severity: {sf.severity}\n"
                    f"  Message: {sf.message}\n"
                    f"  Snippet: {sf.code_snippet or 'N/A'}"
                )
            if len(context.semgrep_findings) > max_semgrep_findings:
                formatted_parts.append(
                    f"... and {len(context.semgrep_findings) - max_semgrep_findings} more Semgrep findings omitted due to budget."
                )

        # 3. Changed Files (Sorted so security-sensitive files are prioritized first)
        formatted_parts.append("\n### [Source: GitHub Diff] Changed Code")
        sorted_files = sorted(
            context.changed_files,
            key=lambda cf: 0 if cls.is_security_sensitive(cf.filename, getattr(cf, 'patch', '') or '') else 1
        )

        for cf in sorted_files[:max_files]:
            formatted_parts.append(f"--- File: {cf.filename} (Status: {cf.status}) ---")
            if hasattr(cf, 'patch') and cf.patch:
                patch = cf.patch[:2500] + "\n...[truncated]" if len(cf.patch) > 2500 else cf.patch
                formatted_parts.append(f"Patch:\n```\n{patch}\n```")

        if len(sorted_files) > max_files:
            formatted_parts.append(f"... and {len(sorted_files) - max_files} more changed files omitted due to context budget.")

        # 4. Tree-Sitter Symbols
        if context.symbol_tables:
            formatted_parts.append("\n### [Source: Tree-sitter AST] Code Symbols & Security Interfaces")
            for symbol in context.symbol_tables[:max_symbols]:
                formatted_parts.append(f"- [{symbol.kind}] {symbol.name} (File: {symbol.file_path})")
            if len(context.symbol_tables) > max_symbols:
                formatted_parts.append(f"... and {len(context.symbol_tables) - max_symbols} more symbols omitted due to budget.")

        # 5. Retrieved Security Documentation
        if context.retrieved_context:
            formatted_parts.append("\n### [Source: Qdrant Vector DB] Repository Security Guidelines & Documentation")
            docs_text = ""
            for doc in context.retrieved_context:
                if isinstance(doc, dict):
                    content = doc.get('page_content', str(doc))
                    source = doc.get('metadata', {}).get('source', 'Security Policy')
                    docs_text += f"[Document: {source}]\n{content}\n\n"
                elif hasattr(doc, 'page_content'):
                    source = getattr(doc, 'metadata', {}).get('source', 'Security Policy')
                    docs_text += f"[Document: {source}]\n{doc.page_content}\n\n"
                else:
                    docs_text += f"{str(doc)}\n\n"

            if len(docs_text) > max_docs_chars:
                docs_text = docs_text[:max_docs_chars] + "\n...[truncated due to context budget]"

            formatted_parts.append(docs_text)

        return "\n".join(formatted_parts)
