import logging
import hashlib
from typing import List, Dict, Any, Optional
from app.github.client import GitHubClient

logger = logging.getLogger(__name__)

class DiscoveredDocument:
    def __init__(self, path: str, content: str, checksum: str, document_type: str):
        self.path = path
        self.content = content
        self.checksum = checksum
        self.document_type = document_type

class RepositoryLoader:
    """
    Discovers and loads documentation files from a GitHub repository.
    """
    def __init__(self, gh_client: GitHubClient, repo_fullname: str, branch: str = "main"):
        self.gh_client = gh_client
        self.repo_fullname = repo_fullname
        self.branch = branch

    def _is_test_file(self, path: str) -> bool:
        lower_path = path.lower()
        if "tests/" in lower_path or "__tests__/" in lower_path:
            return True
        filename = lower_path.split("/")[-1]
        if (
            filename.startswith("test_")
            or filename.endswith("_test.py")
            or filename.endswith(".test.ts")
            or filename.endswith(".spec.ts")
            or filename.endswith(".test.js")
            or filename.endswith(".spec.js")
        ):
            return True
        return False

    def _determine_document_type(self, path: str) -> str:
        if self._is_test_file(path):
            return "TEST_FILE"
        lower_path = path.lower()
        if "readme" in lower_path:
            return "README"
        if "contributing" in lower_path:
            return "CONTRIBUTING"
        if "architecture" in lower_path:
            return "ARCHITECTURE"
        if lower_path.startswith("adr/"):
            return "ADR"
        if lower_path.startswith("docs/api") or "api" in lower_path:
            return "API_DOCS"
        if lower_path.startswith("docs/"):
            return "OTHER"
        return "OTHER"

    def _is_supported_file(self, path: str) -> bool:
        lower_path = path.lower()
        # Ignore source code, images, binaries, node_modules, build folders
        if any(ignore in lower_path for ignore in ["node_modules", "build/", "dist/", ".git", "images/", "assets/"]):
            return False

        if self._is_test_file(path):
            return True
        
        # We explicitly target specific markdown and text files
        if "readme" in lower_path or "contributing" in lower_path or "architecture" in lower_path:
            return True
        if lower_path.startswith("docs/") or lower_path.startswith("adr/"):
            return lower_path.endswith(".md") or lower_path.endswith(".txt")
        return False

    async def discover_documents(self) -> List[DiscoveredDocument]:
        """
        Fetches the repository tree and downloads relevant documentation files.
        """
        endpoint = f"/repos/{self.repo_fullname}/git/trees/{self.branch}?recursive=1"
        response = await self.gh_client.get(endpoint)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch repository tree: {response.text}")
            return []

        tree_data = response.json().get("tree", [])
        discovered_docs = []

        for item in tree_data:
            if item.get("type") != "blob":
                continue
                
            path = item.get("path", "")
            if self._is_supported_file(path):
                # Download raw content
                content_endpoint = f"/repos/{self.repo_fullname}/contents/{path}"
                content_response = await self.gh_client.get(
                    content_endpoint,
                    headers={"Accept": "application/vnd.github.raw"},
                    params={"ref": self.branch}
                )
                
                if content_response.status_code == 200:
                    content = content_response.text
                    checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    doc_type = self._determine_document_type(path)
                    
                    discovered_docs.append(DiscoveredDocument(
                        path=path,
                        content=content,
                        checksum=checksum,
                        document_type=doc_type
                    ))
                else:
                    logger.error(f"Failed to fetch content for {path}: {content_response.text}")

        return discovered_docs
