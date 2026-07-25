from typing import Any, Dict

from langchain_core.runnables import RunnableConfig

from app.github.schemas import GitHubRepository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.repository import repository_service
from app.services.user import user_service
from app.workflows.github_review.state import GitHubReviewState, NormalizedRepository


async def sync_repository(
    state: GitHubReviewState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Sync the repository and owner with the database.
    Outputs the normalized repository context.
    """
    logs = ["Node: Sync Repository started"]
    errors = []

    if state.errors:
        logs.append("Skipping due to previous errors")
        return {"logs": logs}

    db = config["configurable"].get("db_session")
    if not db:
        errors.append("Database session not found in config")
        return {"errors": errors, "logs": logs}

    try:
        # Parse payload using schema
        repo_data = GitHubRepository(**state.raw_payload["repository"])
        owner_data = repo_data.owner

        # 1. Sync User (Repository Owner)
        owner = await user_service.get_user_by_github_id(
            db, github_id=str(owner_data.id)
        )
        if not owner:
            user_in = UserCreate(
                github_id=str(owner_data.id),
                username=owner_data.login,
                avatar_url=owner_data.avatar_url,
                email=owner_data.email,
            )
            owner = await user_service.create_user(db, user_in=user_in)
            logs.append(f"Created user {owner.username}")
        else:
            user_update = UserUpdate(
                username=owner_data.login,
                avatar_url=owner_data.avatar_url,
                email=owner_data.email,
            )
            owner = await user_service.update_user(
                db, db_user=owner, user_in=user_update
            )
            logs.append(f"Updated user {owner.username}")

        # 2. Sync Repository
        repo = await repository_service.get_by_github_repo_id(
            db, github_repo_id=str(repo_data.id)
        )
        if not repo:
            repo_in = RepositoryCreate(
                github_repo_id=str(repo_data.id),
                owner_id=owner.id,
                name=repo_data.name,
                full_name=repo_data.full_name,
                default_branch=repo_data.default_branch,
                installation_id=state.installation_id,
            )
            repo = await repository_service.create_repository(db, repo_in=repo_in)
            logs.append(f"Created repository {repo.full_name}")
        else:
            repo_update = RepositoryUpdate(
                name=repo_data.name,
                full_name=repo_data.full_name,
                default_branch=repo_data.default_branch,
                installation_id=state.installation_id,
            )
            repo = await repository_service.update_repository(
                db, db_repo=repo, repo_in=repo_update
            )
            logs.append(f"Synced repository {repo.full_name}")

        # Create normalized context
        normalized_repo = NormalizedRepository(
            id=str(repo.id),
            github_repo_id=repo.github_repo_id,
            name=repo.name,
            full_name=repo.full_name,
            owner_id=str(repo.owner_id),
            owner_login=owner.username,
            default_branch=repo.default_branch,
            installation_id=repo.installation_id,
        )

        return {"repository": normalized_repo, "logs": logs}

    except Exception as e:
        errors.append(f"Error syncing repository: {str(e)}")
        logs.append("Repository sync failed with exception")
        return {"errors": errors, "logs": logs}
