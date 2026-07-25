import uuid
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState, NormalizedPullRequest
from app.github.schemas import GitHubPullRequest
from app.schemas.pull_request import PullRequestCreate, PullRequestUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.pull_request import pull_request_service
from app.services.user import user_service

async def sync_pull_request(state: GitHubReviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Sync the pull request with the database.
    Outputs the normalized pull request context.
    """
    logs = ["Node: Sync Pull Request started"]
    errors = []

    if state.errors:
        logs.append("Skipping due to previous errors")
        return {"logs": logs}

    if not state.repository:
        errors.append("Repository context missing. Cannot sync PR.")
        return {"errors": errors, "logs": logs}

    db = config["configurable"].get("db_session")
    if not db:
        errors.append("Database session not found in config")
        return {"errors": errors, "logs": logs}

    try:
        pr_data = GitHubPullRequest(**state.raw_payload["pull_request"])
        repo_id = uuid.UUID(state.repository.id)
        
        # We also want to sync the PR author just in case they don't exist
        author_data = pr_data.user
        author = await user_service.get_user_by_github_id(db, github_id=str(author_data.id))
        if not author:
            user_in = UserCreate(
                github_id=str(author_data.id),
                username=author_data.login,
                avatar_url=author_data.avatar_url,
                email=author_data.email
            )
            author = await user_service.create_user(db, user_in=user_in)
            logs.append(f"Created author {author.username}")
        else:
            user_update = UserUpdate(
                username=author_data.login,
                avatar_url=author_data.avatar_url,
                email=author_data.email
            )
            author = await user_service.update_user(db, db_user=author, user_in=user_update)
            logs.append(f"Updated author {author.username}")

        # Check if PR exists
        pr = await pull_request_service.get_by_github_number(
            db, repository_id=repo_id, github_pr_number=pr_data.number
        )

        base_branch = pr_data.base.get("ref", "main") if isinstance(pr_data.base, dict) else "main"
        head_branch = pr_data.head.get("ref", "feature") if isinstance(pr_data.head, dict) else "feature"

        if not pr:
            pr_in = PullRequestCreate(
                github_pr_number=pr_data.number,
                repository_id=repo_id,
                title=pr_data.title,
                description=pr_data.body,
                branch=head_branch,
                base_branch=base_branch,
                state=pr_data.state
            )
            pr = await pull_request_service.create_pull_request(db, pr_in=pr_in)
            logs.append(f"Created pull request #{pr.github_pr_number}")
        else:
            pr_update = PullRequestUpdate(
                title=pr_data.title,
                description=pr_data.body,
                branch=head_branch,
                base_branch=base_branch,
                state=pr_data.state
            )
            pr = await pull_request_service.update_pull_request(db, db_pr=pr, pr_in=pr_update)
            logs.append(f"Synced pull request #{pr.github_pr_number}")

        head_sha_val = pr_data.head.get("sha") if isinstance(pr_data.head, dict) else None

        # Create normalized context
        normalized_pr = NormalizedPullRequest(
            id=str(pr.id),
            github_pr_number=pr.github_pr_number,
            title=pr.title,
            description=pr.description,
            state=pr.state,
            head_branch=pr.branch,
            base_branch=pr.base_branch,
            author_id=str(author.id),
            author_login=author.username,
            head_sha=head_sha_val
        )

        return {"pull_request": normalized_pr, "logs": logs}

    except Exception as e:
        errors.append(f"Error syncing pull request: {str(e)}")
        logs.append("Pull request sync failed with exception")
        return {"errors": errors, "logs": logs}
