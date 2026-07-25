import hmac
import hashlib
from app.core.config import settings

def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook payload was sent from GitHub.
    Uses HMAC with SHA-256 and the GITHUB_WEBHOOK_SECRET.
    """

    """
    This file is responsible for securing our webhook endpoint. Whenever    GitHub sends a webhook, it includes a SHA-256 HMAC signature generated using a shared secret. Our backend recreates that signature using the same secret and the received payload, then securely compares the two using hmac.compare_digest(). If they match, we know the request genuinely came from GitHub and hasn't been tampered with. Otherwise, we reject it with a 401 response. This prevents attackers from sending fake pull request events to our application
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

    
