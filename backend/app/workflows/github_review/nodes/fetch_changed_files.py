import logging
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState
from app.parsers.tree_sitter.models import ChangedFile
from app.github.client import GitHubClient
from app.parsers.tree_sitter.parser_factory import ParserFactory

logger = logging.getLogger(__name__)

async def fetch_changed_files(state: GitHubReviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Fetch the changed files from GitHub Pull Request.
    Skips deleted files and downloads content for added/modified files.
    """
    logs = ["Node: Fetch Changed Files started"]
    errors = []

    if state.errors:
        logs.append("Skipping due to previous errors")
        return {"logs": logs}

    if not state.repository or not state.pull_request:
        errors.append("Missing Repository or PullRequest context in state")
        return {"errors": errors, "logs": logs}

    if not state.installation_id:
        errors.append("Missing installation_id in state")
        return {"errors": errors, "logs": logs}

    # Initialize GitHub client
    gh_client = GitHubClient(state.installation_id)
    repo_fullname = state.repository.full_name
    pr_number = state.pull_request.github_pr_number

    try:
        # 1. Get List of Changed Files
        endpoint = f"/repos/{repo_fullname}/pulls/{pr_number}/files"
        response = await gh_client.get(endpoint)
        
        if response.status_code != 200:
            errors.append(f"Failed to fetch files list from GitHub: {response.text}")
            return {"errors": errors, "logs": logs}

        files_list = response.json()
        changed_files: List[ChangedFile] = []

        logs.append(f"GitHub returned {len(files_list)} changed files in PR")

        # 2. Iterate and download content for non-deleted files
        for f in files_list:
            filename = f.get("filename", "")
            status = f.get("status", "")
            patch = f.get("patch")

            if status == "removed":
                logger.info(f"Skipping deleted file: {filename}")
                logs.append(f"Skipped deleted file: {filename}")
                continue

            # Detect language
            lang = ParserFactory.get_language_name(filename)

            # Get raw file content using contents API with raw media type
            contents_endpoint = f"/repos/{repo_fullname}/contents/{filename}"
            # Need to pass correct ref so we fetch the version at the PR branch (head)
            head_sha = state.raw_payload.get("pull_request", {}).get("head", {}).get("sha")
            
            params = {}
            if head_sha:
                params["ref"] = head_sha

            content_response = await gh_client.get(
                contents_endpoint,
                headers={"Accept": "application/vnd.github.raw"},
                params=params
            )

            if content_response.status_code != 200:
                logger.error(f"Failed to fetch content for {filename}: {content_response.text}")
                logs.append(f"Failed to fetch content for {filename}")
                # We do not fail the whole workflow; we just log it and continue
                continue

            file_content = content_response.text

            changed_files.append(ChangedFile(
                filename=filename.split("/")[-1],
                filepath=filename,
                language=lang,
                patch=patch,
                content=file_content
            ))
            logs.append(f"Fetched file content: {filename} ({lang})")

        logs.append(f"Successfully fetched {len(changed_files)} files")
        return {"changed_files": changed_files, "logs": logs}

    except Exception as e:
        logger.exception(f"Error fetching changed files: {e}")
        errors.append(f"Error fetching changed files: {str(e)}")
        return {"errors": errors, "logs": logs}
