import httpx
from typing import Any

from app.github.auth import get_installation_access_token

class GitHubClient:
    """
    A reusable client for interacting with the GitHub API on behalf of an installation.
    """
    def __init__(self, installation_id: str):
        self.installation_id = installation_id
        self.base_url = "https://api.github.com"
        self._token = None

    async def _get_token(self) -> str:
        if not self._token:
            self._token = await get_installation_access_token(self.installation_id)
        return self._token

    async def get_headers(self) -> dict:
        token = await self._get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        headers = await self.get_headers()
        kwargs["headers"] = {**kwargs.get("headers", {}), **headers}
        
        async with httpx.AsyncClient() as client:
            return await client.get(url, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        url = f"{self.base_url}{endpoint}"
        headers = await self.get_headers()
        kwargs["headers"] = {**kwargs.get("headers", {}), **headers}
        
        async with httpx.AsyncClient() as client:
            return await client.post(url, **kwargs)
