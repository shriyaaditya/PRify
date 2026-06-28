import hmac
import hashlib
from app.core.config import settings

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook payload was sent from GitHub.
    Uses HMAC with SHA-256 and the GITHUB_WEBHOOK_SECRET.
    """
    secret = settings.GITHUB_WEBHOOK_SECRET
    if not secret:
        return False
        
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    hash_object = hmac.new(
        secret.encode("utf-8"),
        msg=payload_body,
        digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)
