import time
import jwt
import httpx
from typing import Optional

from app.core.config import settings

def generate_github_app_jwt() -> str:
    """
    Generate a JWT to authenticate as the GitHub App.
    """
    now = int(time.time())
    # JWT expiration time (10 minute maximum)
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.GITHUB_APP_ID
    }
    
    # Read the private key from settings. It must be in PEM format.
    private_key = settings.GITHUB_PRIVATE_KEY
    if not private_key:
        raise ValueError("GITHUB_PRIVATE_KEY is not set")
    
    # If the key is provided in a single line with escaped newlines, replace them
    private_key = private_key.replace("\\n", "\n")

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
    return encoded_jwt


async def get_installation_access_token(installation_id: str) -> str:
    """
    Obtain an installation access token for a given installation ID.
    """
    app_jwt = generate_github_app_jwt()
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["token"]
