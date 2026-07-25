from app.parsers.tree_sitter.manager import parser_manager
from app.parsers.tree_sitter.models import ParsedFile

class ParserService:
    """
    Service layer providing helper operations around the Tree-sitter parsers.
    """
    def parse_source_code(self, filepath: str, content: str) -> ParsedFile:
        """
        Parses source code into a normalized ParsedFile object.
        """
        return parser_manager.parse_file(filepath, content)

parser_service = ParserService()
