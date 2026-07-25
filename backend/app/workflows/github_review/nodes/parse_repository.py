import logging
from typing import Any, Dict, List

from langchain_core.runnables import RunnableConfig

from app.parsers.tree_sitter.models import ParsedFile, RepositoryStatistics, Symbol
from app.services.parser_service import parser_service
from app.workflows.github_review.state import GitHubReviewState

logger = logging.getLogger(__name__)


async def parse_repository(
    state: GitHubReviewState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    LangGraph node: Parse the changed files, extract AST metadata and Symbol tables,
    and update execution stats.
    """
    logs = ["Node: Parse Repository started"]
    errors = []

    if state.errors:
        logs.append("Skipping due to previous errors")
        return {"logs": logs}

    if not state.changed_files:
        logs.append("No changed files to parse")
        return {
            "parsed_files": [],
            "symbol_tables": [],
            "languages": [],
            "repository_statistics": RepositoryStatistics(
                lines=0, classes=0, functions=0, files_count=0
            ),
            "logs": logs,
        }

    parsed_files: List[ParsedFile] = []
    all_symbols: List[Symbol] = []
    languages_set = set()

    total_lines = 0
    total_classes = 0
    total_functions = 0
    parsed_count = 0

    for file in state.changed_files:
        try:
            logger.info(f"Parsing file: {file.filepath}")
            parsed_file = parser_service.parse_source_code(file.filepath, file.content)

            parsed_files.append(parsed_file)
            all_symbols.extend(parsed_file.symbols)

            if parsed_file.language != "unknown":
                languages_set.add(parsed_file.language)

            file_lines = parsed_file.statistics.get("lines", 0)
            file_classes = parsed_file.statistics.get("classes", 0)
            file_functions = parsed_file.statistics.get("functions", 0)

            total_lines += file_lines
            total_classes += file_classes
            total_functions += file_functions
            parsed_count += 1

            logs.append(
                f"Successfully parsed {file.filepath}: lines={file_lines}, classes={file_classes}, functions={file_functions}"
            )
        except Exception as e:
            logger.error(f"Failed to parse {file.filepath}: {e}")
            logs.append(f"Failed to parse {file.filepath}")
            errors.append(f"Parsing failed for {file.filepath}: {str(e)}")

    repository_statistics = RepositoryStatistics(
        lines=total_lines,
        classes=total_classes,
        functions=total_functions,
        files_count=parsed_count,
    )

    return {
        "parsed_files": parsed_files,
        "symbol_tables": all_symbols,
        "languages": list(languages_set),
        "repository_statistics": repository_statistics,
        "errors": errors,
        "logs": logs,
    }
