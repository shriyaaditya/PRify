import logging
import re
from typing import Dict, Any, List
from langchain_core.runnables import RunnableConfig

from app.workflows.github_review.state import GitHubReviewState
from app.schemas.semgrep import SemgrepFinding

logger = logging.getLogger(__name__)

async def analyze_semgrep(state: GitHubReviewState, config: RunnableConfig) -> Dict[str, Any]:
    """
    LangGraph node: Perform static security analysis on changed files using Semgrep rules or regex pattern heuristics.
    Normalizes findings into SemgrepFinding instances.
    """
    logs = ["Node: Analyze Semgrep started"]
    errors = []

    if state.errors:
        logs.append("Skipping Semgrep analysis due to previous errors")
        return {"logs": logs}

    if not state.changed_files:
        logs.append("No changed files to analyze with Semgrep")
        return {
            "semgrep_findings": [],
            "logs": logs
        }

    semgrep_findings: List[SemgrepFinding] = []

    # Heuristic Security Pattern Matcher (Fallback / Native analyzer)
    SECURITY_PATTERNS = [
        {
            "rule_id": "generic.security.audit.hardcoded-secret",
            "regex": r"(?i)(api[_-]?key|secret[_-]?key|password|auth[_-]?token)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
            "severity": "ERROR",
            "message": "Possible hardcoded secret or credential detected in source code."
        },
        {
            "rule_id": "generic.security.audit.sqli-raw-query",
            "regex": r"(?i)(SELECT|INSERT|UPDATE|DELETE).*\+.*|\.execute\s*\(\s*f['\"].*\{|\.execute\s*\(\s*['\"].*%s",
            "severity": "ERROR",
            "message": "Potential SQL injection vulnerability via string concatenation in query execution."
        },
        {
            "rule_id": "generic.security.audit.command-injection",
            "regex": r"(os\.system|subprocess\.Popen|eval|exec)\s*\(",
            "severity": "ERROR",
            "message": "Use of unsafe system execution calls may lead to command injection."
        },
        {
            "rule_id": "generic.security.audit.path-traversal",
            "regex": r"open\s*\(\s*.*\+.*|\.send_file\s*\(\s*.*request\.",
            "severity": "WARNING",
            "message": "Potential path traversal flaw when opening user-supplied file paths."
        }
    ]

    for file in state.changed_files:
        if not file.content:
            continue

        lines = file.content.splitlines()
        for idx, line_text in enumerate(lines, start=1):
            for pattern in SECURITY_PATTERNS:
                if re.search(pattern["regex"], line_text):
                    finding = SemgrepFinding(
                        rule_id=pattern["rule_id"],
                        file_path=file.filename or file.filepath,
                        line_number=idx,
                        severity=pattern["severity"],
                        message=pattern["message"],
                        code_snippet=line_text.strip()
                    )
                    semgrep_findings.append(finding)
                    logs.append(f"Semgrep finding [{pattern['rule_id']}] at {file.filename}:{idx}")

    logger.info(f"Semgrep analysis complete. Found {len(semgrep_findings)} potential static findings.")
    logs.append(f"Semgrep analysis finished with {len(semgrep_findings)} findings.")

    return {
        "semgrep_findings": semgrep_findings,
        "errors": errors,
        "logs": logs
    }
