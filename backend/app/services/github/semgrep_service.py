import asyncio
import json
import logging
import os
import shutil
import tempfile
from typing import Dict, List, Optional

from app.core.config import settings
from app.parsers.tree_sitter.models import ChangedFile
from app.schemas.semgrep import SemgrepFinding

logger = logging.getLogger(__name__)

SEMGREP_SEVERITY_MAP: Dict[str, str] = {
    "ERROR": "ERROR",
    "WARNING": "WARNING",
    "INFO": "INFO",
}


class SemgrepService:
    """
    Service adapter for executing real Semgrep CLI static analysis asynchronously against changed files.
    """

    SUPPORTED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

    def __init__(self, rules: Optional[str] = None, timeout: Optional[int] = None):
        self.rules = rules or settings.SEMGREP_RULES
        self.timeout = timeout or settings.SEMGREP_TIMEOUT_SECONDS

    def _is_safe_relative_path(self, filepath: str) -> bool:
        """
        Verify that filepath is relative and does not escape via path traversal.
        """
        if not filepath or filepath.startswith("/") or ".." in filepath.split("/"):
            return False
        return True

    def map_severity(self, raw_severity: str) -> str:
        """
        Map Semgrep CLI severity string to internal severity enum format.
        """
        return SEMGREP_SEVERITY_MAP.get(str(raw_severity).upper(), "WARNING")

    def parse_semgrep_json(self, raw_json_str: str) -> List[SemgrepFinding]:
        """
        Parse raw Semgrep JSON output into normalized SemgrepFinding list.
        """
        findings: List[SemgrepFinding] = []
        if not raw_json_str or not raw_json_str.strip():
            return findings

        try:
            data = json.loads(raw_json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Semgrep JSON output: {e}")
            return findings

        results = data.get("results", [])
        for item in results:
            rule_id = item.get("check_id") or item.get("extra", {}).get(
                "rule_id", "semgrep.rule"
            )
            raw_path = item.get("path", "")

            # Clean temporary prefix if present
            clean_path = raw_path
            if "tmp" in clean_path and "/" in clean_path:
                parts = clean_path.split("/")
                # Attempt to strip temporary directory components up to the relative repo path
                clean_path = (
                    "/".join(parts[parts.index("tmp") + 2 :])
                    if "tmp" in parts
                    else clean_path
                )

            start_line = item.get("start", {}).get("line", 1)
            extra = item.get("extra", {})
            message = extra.get("message") or item.get("extra", {}).get(
                "message", "Semgrep security finding."
            )
            raw_sev = extra.get("severity", "WARNING")
            code_snippet = extra.get("lines", "").strip() or None

            findings.append(
                SemgrepFinding(
                    rule_id=rule_id,
                    file_path=clean_path,
                    line_number=start_line,
                    severity=self.map_severity(raw_sev),
                    message=message,
                    code_snippet=code_snippet,
                )
            )

        return findings

    async def run_analysis(
        self, changed_files: List[ChangedFile]
    ) -> List[SemgrepFinding]:
        """
        Runs Semgrep CLI asynchronously against temporary file representations of changed files.
        """
        semgrep_bin = shutil.which("semgrep")
        if not semgrep_bin:
            logger.warning(
                "Semgrep CLI executable not found on system PATH. Skipping static analysis."
            )
            return []

        # Filter supported, non-deleted files
        target_files = [
            f
            for f in changed_files
            if f.content
            and any(
                f.filepath.lower().endswith(ext) for ext in self.SUPPORTED_EXTENSIONS
            )
        ]

        if not target_files:
            logger.info(
                "No changed source files matching supported extensions for Semgrep scan."
            )
            return []

        temp_dir = tempfile.mkdtemp(prefix="semgrep_scan_")
        try:
            # 1. Reconstruct files in isolated temporary workspace with path traversal defense
            staged_paths = []
            for cf in target_files:
                if not self._is_safe_relative_path(cf.filepath):
                    logger.warning(
                        f"Unsafe file path detected and skipped: {cf.filepath}"
                    )
                    continue

                abs_target_path = os.path.abspath(os.path.join(temp_dir, cf.filepath))
                if not abs_target_path.startswith(os.path.abspath(temp_dir)):
                    logger.warning(f"Path traversal blocked for file: {cf.filepath}")
                    continue

                os.makedirs(os.path.dirname(abs_target_path), exist_ok=True)
                with open(abs_target_path, "w", encoding="utf-8") as f:
                    f.write(cf.content)

                staged_paths.append(cf.filepath)

            if not staged_paths:
                return []

            # 2. Build Semgrep CLI argument list (no shell=True)
            cmd = [
                semgrep_bin,
                "scan",
                "--config",
                self.rules,
                "--json",
                "--quiet",
                "--no-git-ignore",
                temp_dir,
            ]

            logger.info(f"Executing Semgrep CLI: {' '.join(cmd)}")

            # 3. Execute subprocess asynchronously
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Semgrep CLI execution timed out after {self.timeout}s. Terminating process."
                )
                try:
                    res = proc.kill()
                    if asyncio.iscoroutine(res):
                        await res
                    await proc.wait()
                except Exception as kill_err:
                    logger.error(f"Failed to kill Semgrep process: {kill_err}")
                return []

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            # Semgrep exits 0 on success/findings found, or 1 if findings are found depending on config.
            if proc.returncode not in (0, 1):
                logger.error(
                    f"Semgrep CLI failed with exit code {proc.returncode}: {stderr_str}"
                )
                if not stdout_str:
                    return []

            # 4. Parse Semgrep JSON output and remap relative filepaths
            findings = self.parse_semgrep_json(stdout_str)

            # Ensure filepaths match exact original repository-relative paths
            norm_temp_dir = os.path.abspath(temp_dir)
            normalized_findings: List[SemgrepFinding] = []
            for f in findings:
                rel_path = f.file_path
                if os.path.isabs(rel_path) and rel_path.startswith(norm_temp_dir):
                    rel_path = os.path.relpath(rel_path, norm_temp_dir)

                normalized_findings.append(
                    SemgrepFinding(
                        rule_id=f.rule_id,
                        file_path=rel_path,
                        line_number=f.line_number,
                        severity=f.severity,
                        message=f.message,
                        code_snippet=f.code_snippet,
                    )
                )

            logger.info(
                f"Semgrep CLI scan complete. Produced {len(normalized_findings)} findings."
            )
            return normalized_findings

        except Exception as e:
            logger.exception(f"Unexpected error during Semgrep execution: {e}")
            return []
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


semgrep_service = SemgrepService()
