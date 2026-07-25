import logging
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from app.services.github.semgrep_service import semgrep_service
from app.workflows.github_review.state import GitHubReviewState

logger = logging.getLogger(__name__)


async def analyze_semgrep(
    state: GitHubReviewState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    LangGraph node: Perform static security analysis on changed files using real Semgrep CLI.
    Delegates CLI execution and JSON parsing to SemgrepService.
    """
    logs = ["Node: Analyze Semgrep started"]
    errors = []

    if state.errors:
        logs.append("Skipping Semgrep analysis due to previous errors")
        return {"logs": logs}

    if not state.changed_files:
        logs.append("No changed files to analyze with Semgrep")
        return {"semgrep_findings": [], "logs": logs}

    try:
        semgrep_findings = await semgrep_service.run_analysis(state.changed_files)
        logger.info(
            f"Semgrep node execution finished with {len(semgrep_findings)} findings."
        )
        logs.append(f"Semgrep analysis finished with {len(semgrep_findings)} findings.")

        return {"semgrep_findings": semgrep_findings, "errors": errors, "logs": logs}
    except Exception as e:
        logger.error(f"Error during Semgrep node execution: {e}")
        errors.append(f"Semgrep analysis error: {str(e)}")
        return {"semgrep_findings": [], "errors": errors, "logs": logs}
