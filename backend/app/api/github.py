import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response

from app.github.webhook import verify_signature
from app.workflows.github_review.service import process_github_review

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for receiving GitHub App webhooks.
    Validates signature and event, schedules background review task, and acknowledges immediately.
    """
    # 1. Read the raw body to verify signature
    body = await request.body()
    signature_header = request.headers.get("X-Hub-Signature-256", "")

    if not verify_signature(body, signature_header):
        logger.error("Invalid GitHub webhook signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info("GitHub webhook signature verified")

    # 2. Extract Event Type
    event = request.headers.get("X-GitHub-Event")
    if not event:
        logger.warning("Missing X-GitHub-Event header")
        return Response(status_code=400, content="Missing X-GitHub-Event header")

    # We only process pull_request events in this workflow
    if event != "pull_request":
        logger.info(f"Ignoring unhandled GitHub event type: {event}")
        return {"status": "ignored", "reason": f"Unsupported event type: {event}"}

    # 3. Parse JSON payload
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    action = data.get("action")
    allowed_actions = {"opened", "synchronize", "reopened"}
    if action not in allowed_actions:
        logger.info(f"Ignoring unhandled pull_request action: {action}")
        return {"status": "ignored", "reason": f"Unsupported action: {action}"}

    installation_id = data.get("installation", {}).get("id")
    if installation_id:
        installation_id = str(installation_id)

    # 4. Schedule background task with durable values only (no request-scoped objects)
    background_tasks.add_task(
        process_github_review,
        event_type=event,
        action=action,
        installation_id=installation_id,
        raw_payload=data,
    )

    logger.info("Successfully scheduled GitHub review background task")
    return Response(
        status_code=202,
        content='{"status": "accepted", "message": "Review workflow scheduled in background"}',
        media_type="application/json",
    )
