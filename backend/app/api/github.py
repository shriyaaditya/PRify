import logging
import json
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.github.webhook import verify_signature
from app.workflows.github_review.graph import graph
from app.workflows.github_review.state import GitHubReviewState
from langchain_core.runnables import RunnableConfig

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

    # 3. Parse JSON payload
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    # 4. Initialize Graph State
    action = data.get("action")
    installation_id = data.get("installation", {}).get("id")
    if installation_id:
        installation_id = str(installation_id)

    initial_state = GitHubReviewState(
        event_type=event,
        action=action,
        installation_id=installation_id,
        raw_payload=data
    )

    # 5. Invoke LangGraph Workflow
    config = RunnableConfig(configurable={"db_session": db})
    try:
        final_state = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        logger.exception(f"Error during LangGraph execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # 6. Evaluate Workflow Results
    if final_state.get("errors"):
        logger.error(f"Workflow finished with errors: {final_state['errors']}")
        # Return 200 so GitHub does not retry continuously on validation/logic failures,
        # but could also return 400 depending on the design pattern.
        # Following typical webhook patterns, returning 200 if we successfully processed it,
        # even if it was a validation rejection or skipping.
        return {"status": "error", "details": final_state["errors"]}

    return {"status": "ok"}

