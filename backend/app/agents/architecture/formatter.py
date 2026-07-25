import json
from typing import List, Dict, Any, Optional
from app.agents.base.context import ReviewContext

class ContextFormatter:
    """
    Formats the ReviewContext into a token-efficient string for the LLM.
    Preserves exact information sources and respects configurable context budgets to prevent exceeding token limits.
    """
    
    @staticmethod
    def format_for_architecture(
        context: ReviewContext,
        max_files: int = 10,
        max_symbols: int = 30,
        max_docs_chars: int = 4000
    ) -> str:
        """
        Formats context specifically for architectural review.
        Labeling each source explicitly (GitHub Diff, Tree-sitter AST, Qdrant Vector DB).
        """
        formatted_parts = []
        
        # 1. PR Metadata (GitHub PR Payload Source)
        formatted_parts.append("### [Source: GitHub PR Metadata] Pull Request Context")
        formatted_parts.append(f"Title: {context.pull_request.title}")
        if context.pull_request.description:
            formatted_parts.append(f"Description: {context.pull_request.description}")
        
        # 2. Changed Files (GitHub Diff Source)
        formatted_parts.append("\n### [Source: GitHub Diff] Changed Code")
        for cf in context.changed_files[:max_files]:
            formatted_parts.append(f"--- File: {cf.filename} (Status: {cf.status}) ---")
            if hasattr(cf, 'patch') and cf.patch:
                patch = cf.patch[:2000] + "\n...[truncated]" if len(cf.patch) > 2000 else cf.patch
                formatted_parts.append(f"Patch:\n```\n{patch}\n```")
                
        if len(context.changed_files) > max_files:
            formatted_parts.append(f"... and {len(context.changed_files) - max_files} more changed files omitted due to context budget.")
            
        # 3. Tree-Sitter Symbols (Tree-sitter AST Source)
        if context.symbol_tables:
            formatted_parts.append("\n### [Source: Tree-sitter AST] Code Symbols & Interfaces")
            for symbol in context.symbol_tables[:max_symbols]:
                formatted_parts.append(f"- [{symbol.kind}] {symbol.name} (File: {symbol.file_path})")
            if len(context.symbol_tables) > max_symbols:
                formatted_parts.append(f"... and {len(context.symbol_tables) - max_symbols} more symbols omitted due to context budget.")
                
        # 4. Retrieved Documentation (Qdrant Vector DB Source)
        if context.retrieved_context:
            formatted_parts.append("\n### [Source: Qdrant Vector DB] Architecture Documentation & Guidelines")
            docs_text = ""
            for doc in context.retrieved_context:
                if isinstance(doc, dict):
                    content = doc.get('page_content', str(doc))
                    source = doc.get('metadata', {}).get('source', 'Architecture Guideline')
                    docs_text += f"[Document: {source}]\n{content}\n\n"
                elif hasattr(doc, 'page_content'):
                    source = getattr(doc, 'metadata', {}).get('source', 'Architecture Guideline')
                    docs_text += f"[Document: {source}]\n{doc.page_content}\n\n"
                else:
                    docs_text += f"{str(doc)}\n\n"
            
            if len(docs_text) > max_docs_chars:
                docs_text = docs_text[:max_docs_chars] + "\n...[truncated due to context budget]"
                
            formatted_parts.append(docs_text)
            
        return "\n".join(formatted_parts)
