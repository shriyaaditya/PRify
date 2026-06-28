import logging
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.github.webhook import verify_signature
from app.github.schemas import WebhookPayload
from app.github.service import webhook_service
from pydantic import ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def github_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Endpoint for receiving GitHub App webhooks.
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

    # We only care about pull_request events for now
    if event != "pull_request":
        logger.info(f"Ignored non-pull-request event: {event}")
        return Response(status_code=200, content=f"Event {event} ignored")

    # 3. Parse JSON payload
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        payload = WebhookPayload(**data)
    except ValidationError as e:
        logger.error(f"Payload validation error: {e}")
        # Return 200 to prevent GitHub from retrying invalid format permanently,
        # or 400 depending on preference. GitHub recommends 2xx if received successfully.
        raise HTTPException(status_code=400, detail="Invalid payload structure")

    # 4. Filter actions
    allowed_actions = {"opened", "synchronize", "reopened"}
    if payload.action not in allowed_actions:
        logger.info(f"Ignored pull_request action: {payload.action}")
        return Response(status_code=200, content=f"Action {payload.action} ignored")

    # 5. Process Payload
    try:
        await webhook_service.process_pull_request_event(db, payload)
    except Exception as e:
        logger.exception(f"Error processing pull request event: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"status": "ok"}
