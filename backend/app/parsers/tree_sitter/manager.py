import logging
from typing import Optional
from app.parsers.tree_sitter.parser_factory import ParserFactory
from app.parsers.tree_sitter.models import ParsedFile

logger = logging.getLogger(__name__)

class ParserManager:
    """
    Manages loading and caching parser instances, presenting a single public API for file parsing.
    """
    def __init__(self):
        self._parsers = {}

    def parse_file(self, filepath: str, source_code: str) -> ParsedFile:
        """
        Public API to parse a source file by delegating to the appropriate Language Parser.
        """
        parser = ParserFactory.get_parser(filepath)
        source_bytes = source_code.encode("utf-8")

        if not parser:
            # Fallback for unsupported file types: return basic statistics without structural AST
            lines = source_code.splitlines()
            logger.info(f"No specific parser found for {filepath}. Using fallback parsing.")
            return ParsedFile(
                filepath=filepath,
                language=ParserFactory.get_language_name(filepath),
                statistics={"lines": len(lines), "classes": 0, "functions": 0}
            )

        try:
            return parser.parse(filepath, source_bytes)
        except Exception as e:
            logger.error(f"Error parsing file {filepath} with {parser.__class__.__name__}: {e}")
            lines = source_code.splitlines()
            return ParsedFile(
                filepath=filepath,
                language=ParserFactory.get_language_name(filepath),
                statistics={"lines": len(lines), "classes": 0, "functions": 0}
            )

parser_manager = ParserManager()
