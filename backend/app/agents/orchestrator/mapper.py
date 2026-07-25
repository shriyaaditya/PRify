from typing import Any
from app.workflows.github_review.state import GitHubReviewState
from app.agents.base.context import ReviewContext

class ContextMapper:
    """
    Responsible for mapping the LangGraph workflow state to the immutable ReviewContext.
    """
    
    @staticmethod
    def map_from_state(state: GitHubReviewState) -> ReviewContext:
        """
        Creates an immutable ReviewContext from the GitHubReviewState.
        """
        if not state.repository:
            raise ValueError("State is missing 'repository' which is required for ReviewContext.")
        if not state.pull_request:
            raise ValueError("State is missing 'pull_request' which is required for ReviewContext.")
            
        return ReviewContext(
            repository=state.repository,
            pull_request=state.pull_request,
            changed_files=state.changed_files,
            parsed_files=state.parsed_files,
            symbol_tables=state.symbol_tables,
            semgrep_findings=state.semgrep_findings,
            retrieved_context=state.retrieved_context,
            metadata={
                "event_type": state.event_type,
                "action": state.action,
                "installation_id": state.installation_id
            },
            repository_summary=state.repository_summary
        )
