import hashlib
import logging
from typing import List

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

    def __init__(
        self, gh_client: GitHubClient, repo_fullname: str, branch: str = "main"
    ):
        self.gh_client = gh_client
        self.repo_fullname = repo_fullname
        self.branch = branch

    # Supported source code file extensions
    SUPPORTED_CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

    # Directories to explicitly exclude from indexing
    EXCLUDED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".next",
        "coverage",
        "__pycache__",
        "qdrant_storage",
        ".pytest_cache",
    }

    # Sensitive or uninformative file patterns to exclude
    EXCLUDED_FILES = {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        ".env.example",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
    }

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

        # Check source code extensions
        filename = lower_path.split("/")[-1]
        for ext in self.SUPPORTED_CODE_EXTENSIONS:
            if filename.endswith(ext):
                return "SOURCE_CODE"

        return "OTHER"

    def _is_supported_file(self, path: str) -> bool:
        parts = path.split("/")
        filename = parts[-1].lower()

        # 1. Check directory exclusions
        for part in parts[:-1]:
            if part.lower() in self.EXCLUDED_DIRS:
                return False

        # 2. Check sensitive/lockfile exclusions
        if filename in self.EXCLUDED_FILES or filename.startswith(".env"):
            return False

        # 3. Check test files
        if self._is_test_file(path):
            return True

        # 4. Check supported documentation files
        lower_path = path.lower()
        if (
            "readme" in lower_path
            or "contributing" in lower_path
            or "architecture" in lower_path
        ):
            return True
        if lower_path.startswith("docs/") or lower_path.startswith("adr/"):
            if lower_path.endswith(".md") or lower_path.endswith(".txt"):
                return True

        # 5. Check supported source code extensions
        for ext in self.SUPPORTED_CODE_EXTENSIONS:
            if filename.endswith(ext):
                return True

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
                    params={"ref": self.branch},
                )

                if content_response.status_code == 200:
                    content = content_response.text
                    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
                    doc_type = self._determine_document_type(path)

                    discovered_docs.append(
                        DiscoveredDocument(
                            path=path,
                            content=content,
                            checksum=checksum,
                            document_type=doc_type,
                        )
                    )
                else:
                    logger.error(
                        f"Failed to fetch content for {path}: {content_response.text}"
                    )

        return discovered_docs
