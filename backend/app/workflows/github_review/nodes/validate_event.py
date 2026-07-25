from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState


async def validate_event(
    state: GitHubReviewState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Validate the incoming GitHub event and payload.
    Ensures that the event is supported and extracts necessary information.
    """
    logs = ["Node: Validate Event started"]
    errors = []

    try:
        # We only support pull_request events in this workflow
        if state.event_type != "pull_request":
            errors.append(f"Unsupported event type: {state.event_type}")
            logs.append("Validation failed: Unsupported event")
            return {"errors": errors, "logs": logs}

        allowed_actions = {"opened", "synchronize", "reopened"}
        if state.action not in allowed_actions:
            errors.append(f"Unsupported pull_request action: {state.action}")
            logs.append("Validation failed: Unsupported action")
            return {"errors": errors, "logs": logs}

        if "repository" not in state.raw_payload:
            errors.append("Missing 'repository' in payload")

        if "pull_request" not in state.raw_payload:
            errors.append("Missing 'pull_request' in payload")

        if not errors:
            logs.append("Validation successful")
    except Exception as e:
        errors.append(f"Error during validation: {str(e)}")
        logs.append("Validation failed with exception")

    return {"errors": errors, "logs": logs}
