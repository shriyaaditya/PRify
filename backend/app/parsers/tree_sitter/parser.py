from abc import ABC, abstractmethod
from app.parsers.tree_sitter.models import ParsedFile

class BaseLanguageParser(ABC):
    """
    Abstract base class for all language-specific parsers.
    """
    @abstractmethod
    def parse(self, filepath: str, source_code: bytes) -> ParsedFile:
        """
        Parses raw file bytes and extracts AST nodes and Symbol tables.
        """
        pass
