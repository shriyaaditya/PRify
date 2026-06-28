import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.github.schemas import WebhookPayload
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.schemas.pull_request import PullRequestCreate, PullRequestUpdate
from app.services.user import user_service
from app.services.repository import repository_service
from app.services.pull_request import pull_request_service

logger = logging.getLogger(__name__)

class GitHubWebhookService:
    async def process_pull_request_event(self, db: AsyncSession, payload: WebhookPayload) -> None:
        """
        Process pull_request events from GitHub.
        Syncs User (Owner/Author), Repository, and PullRequest records to the database.
        """
        if not payload.pull_request:
            logger.warning("No pull_request object in payload.")
            return

        logger.info(f"Processing PR event '{payload.action}' for PR #{payload.pull_request.number}")
        
        # 1. Sync User (Repository Owner)
        owner_data = payload.repository.owner
        owner = await user_service.get_user_by_github_id(db, github_id=str(owner_data.id))
        
        if not owner:
            user_in = UserCreate(
                github_id=str(owner_data.id),
                username=owner_data.login,
                avatar_url=owner_data.avatar_url,
                email=owner_data.email
            )
            owner = await user_service.create_user(db, user_in=user_in)
            logger.info(f"Created new user {owner.username} (github_id: {owner.github_id})")
        else:
            # Optionally update avatar/email if changed
            user_update = UserUpdate(
                username=owner_data.login,
                avatar_url=owner_data.avatar_url,
                email=owner_data.email
            )
            owner = await user_service.update_user(db, db_user=owner, user_in=user_update)

        # 2. Sync Repository
        repo_data = payload.repository
        repo = await repository_service.get_by_github_repo_id(db, github_repo_id=str(repo_data.id))
        installation_id = str(payload.installation.id) if payload.installation else None

        if not repo:
            repo_in = RepositoryCreate(
                github_repo_id=str(repo_data.id),
                owner_id=owner.id,
                name=repo_data.name,
                full_name=repo_data.full_name,
                default_branch=repo_data.default_branch,
                installation_id=installation_id
            )
            repo = await repository_service.create_repository(db, repo_in=repo_in)
            logger.info(f"Created new repository {repo.full_name}")
        else:
            repo_update = RepositoryUpdate(
                name=repo_data.name,
                full_name=repo_data.full_name,
                default_branch=repo_data.default_branch,
                installation_id=installation_id
            )
            repo = await repository_service.update_repository(db, db_repo=repo, repo_in=repo_update)
            logger.info(f"Synced repository {repo.full_name}")

        # 3. Sync Pull Request
        pr_data = payload.pull_request
        pr = await pull_request_service.get_by_github_number(
            db, repository_id=repo.id, github_pr_number=pr_data.number
        )
        
        base_branch = pr_data.base.get("ref", "main") if isinstance(pr_data.base, dict) else "main"
        head_branch = pr_data.head.get("ref", "feature") if isinstance(pr_data.head, dict) else "feature"
        
        if not pr:
            pr_in = PullRequestCreate(
                github_pr_number=pr_data.number,
                repository_id=repo.id,
                title=pr_data.title,
                description=pr_data.body,
                branch=head_branch,
                base_branch=base_branch,
                state=pr_data.state
            )
            pr = await pull_request_service.create_pull_request(db, pr_in=pr_in)
            logger.info(f"Created new PR #{pr.github_pr_number} in {repo.full_name}")
        else:
            pr_update = PullRequestUpdate(
                title=pr_data.title,
                description=pr_data.body,
                branch=head_branch,
                base_branch=base_branch,
                state=pr_data.state
            )
            pr = await pull_request_service.update_pull_request(db, db_pr=pr, pr_in=pr_update)
            logger.info(f"Synced PR #{pr.github_pr_number} in {repo.full_name}")


webhook_service = GitHubWebhookService()
