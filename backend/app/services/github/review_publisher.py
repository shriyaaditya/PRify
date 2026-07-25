import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.github.client import GitHubClient
from app.github.review_formatter import GitHubReviewFormatter
from app.agents.consensus.models import ConsensusReviewResult
from app.parsers.tree_sitter.models import ChangedFile
from app.models.enums import ReviewStatus, Severity
from app.schemas.review import ReviewCreate, ReviewUpdate, ReviewFindingCreate
from app.services.review import review_service

logger = logging.getLogger(__name__)

class ReviewPublisherService:
    """
    Service responsible for publishing ConsensusReviewResult as a GitHub PR Review.
    Enforces PostgreSQL-based idempotency on (pull_request_id, commit_sha/head_sha).
    """

    async def publish_review(
        self,
        installation_id: str,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        pull_request_id: Optional[str],
        head_sha: Optional[str],
        consensus_result: ConsensusReviewResult,
        changed_files: List[ChangedFile],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Publishes review to GitHub API if not already published for this PR commit SHA in PostgreSQL.
        """
        pr_uuid = uuid.UUID(pull_request_id) if pull_request_id else None
        effective_sha = head_sha or "HEAD"

        # 1. PostgreSQL Idempotency Check
        if db and pr_uuid and head_sha:
            existing_review = await review_service.get_by_pull_request_and_commit_sha(
                db, pull_request_id=pr_uuid, commit_sha=head_sha
            )
            if existing_review and existing_review.status == ReviewStatus.COMPLETED and existing_review.github_review_id:
                logger.info(f"Review already published for PR {pr_number} commit {head_sha} (GitHub Review ID: {existing_review.github_review_id}). Skipping duplicate publishing.")
                return {
                    "published": False,
                    "skipped": True,
                    "github_review_id": existing_review.github_review_id,
                    "reason": f"Review already published for commit {head_sha}"
                }

        # 2. Format GitHub Review Payload (Deterministic, conservative diff line mapping)
        payload = GitHubReviewFormatter.format_github_review_payload(
            consensus_result=consensus_result,
            changed_files=changed_files
        )

        logger.info(f"Publishing PR review to {repo_owner}/{repo_name}#{pr_number} for commit {effective_sha} with {len(payload.get('comments', []))} inline comments.")

        # 3. Call GitHub API
        try:
            gh_client = GitHubClient(installation_id=installation_id)
            endpoint = f"/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/reviews"
            
            response = await gh_client.post(endpoint, json=payload)
            
            if response.status_code in (200, 201):
                resp_data = response.json()
                github_review_id = str(resp_data.get("id", "N/A"))
                logger.info(f"Successfully published GitHub review {github_review_id} for PR #{pr_number}.")

                # 4. Persist Review record in PostgreSQL upon successful publication
                if db and pr_uuid:
                    review_in = ReviewCreate(
                        pull_request_id=pr_uuid,
                        status=ReviewStatus.COMPLETED,
                        commit_sha=effective_sha,
                        github_review_id=github_review_id,
                        overall_summary=consensus_result.summary
                    )
                    db_review = await review_service.create_review(db, review_in=review_in)

                    # Store consensus findings in DB
                    for finding in consensus_result.findings:
                        sev_enum = Severity.MEDIUM
                        try:
                            sev_enum = Severity(finding.severity.capitalize())
                        except Exception:
                            pass

                        finding_in = ReviewFindingCreate(
                            review_id=db_review.id,
                            agent_name="ConsensusAgent",
                            title=finding.title,
                            description=finding.summary,
                            severity=sev_enum,
                            confidence=finding.confidence,
                            file_path=finding.file_path,
                            line_number=finding.line_number,
                            recommendation=finding.recommendation
                        )
                        await review_service.create_finding(db, finding_in=finding_in)

                return {
                    "published": True,
                    "github_review_id": github_review_id,
                    "inline_comments_count": len(payload.get("comments", [])),
                    "summary": consensus_result.summary
                }
            else:
                err_msg = f"GitHub API review creation failed with HTTP {response.status_code}: {response.text}"
                logger.error(err_msg)
                return {
                    "published": False,
                    "error": err_msg
                }

        except Exception as e:
            err_msg = f"Exception during GitHub review publishing: {str(e)}"
            logger.error(err_msg, exc_info=True)
            return {
                "published": False,
                "error": err_msg
            }


review_publisher_service = ReviewPublisherService()
