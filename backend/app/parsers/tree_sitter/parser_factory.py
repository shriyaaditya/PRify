import os
from typing import Optional
from app.parsers.tree_sitter.parser import BaseLanguageParser
from app.parsers.tree_sitter.languages.python_parser import PythonParser
from app.parsers.tree_sitter.languages.javascript_parser import JavaScriptParser
from app.parsers.tree_sitter.languages.typescript_parser import TypeScriptParser

class ParserFactory:
    """
    Factory to resolve and instantiate the correct Language Parser based on file extension.
    """
    @staticmethod
    def get_parser(filepath: str) -> Optional[BaseLanguageParser]:
        _, ext = os.path.splitext(filepath.lower())
        
        if ext == ".py":
            return PythonParser()
        elif ext in (".js", ".jsx"):
            return JavaScriptParser()
        elif ext == ".ts":
            return TypeScriptParser(is_tsx=False)
        elif ext == ".tsx":
            return TypeScriptParser(is_tsx=True)
        
        return None

    @staticmethod
    def get_language_name(filepath: str) -> str:
        _, ext = os.path.splitext(filepath.lower())
        if ext == ".py":
            return "python"
        elif ext == ".js":
            return "javascript"
        elif ext == ".jsx":
            return "javascript-react"
        elif ext == ".ts":
            return "typescript"
        elif ext == ".tsx":
            return "typescript-react"
        return "unknown"
class ParserFactory:
    """
    Factory to resolve and instantiate the correct Language Parser based on file extension.
    """
    @staticmethod
    def get_parser(filepath: str) -> Optional[BaseLanguageParser]:
        _, ext = os.path.splitext(filepath.lower())
        
        if ext == ".py":
            return PythonParser()
        elif ext in (".js", ".jsx"):
            return JavaScriptParser()
        elif ext == ".ts":
            return TypeScriptParser(is_tsx=False)
        elif ext == ".tsx":
            return TypeScriptParser(is_tsx=True)
        
        return None

    @staticmethod
    def get_language_name(filepath: str) -> str:
        _, ext = os.path.splitext(filepath.lower())
        if ext == ".py":
            return "python"
        elif ext == ".js":
            return "javascript"
        elif ext == ".jsx":
            return "javascript-react"
        elif ext == ".ts":
            return "typescript"
        elif ext == ".tsx":
            return "typescript-react"
        return "unknown"
