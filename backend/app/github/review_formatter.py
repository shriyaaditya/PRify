import re
from typing import Any, Dict, List

from app.agents.consensus.models import ConsensusFinding, ConsensusReviewResult
from app.parsers.tree_sitter.models import ChangedFile


class GitHubReviewFormatter:
    """
    Deterministic formatter that converts ConsensusReviewResult into a GitHub PR Review payload.
    Maps inline findings strictly to valid RIGHT-side lines in PR diff patches.
    """

    HUNK_HEADER_PATTERN = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")

    @classmethod
    def is_line_in_diff(cls, patch: str, line_number: int) -> bool:
        """
        Conservatively checks whether line_number corresponds to a valid added (+) or context ( )
        line on the RIGHT side of a unified diff patch.
        """
        if not patch or line_number is None or line_number <= 0:
            return False

        lines = patch.split("\n")
        current_new_line = 0
        in_hunk = False

        for line in lines:
            match = cls.HUNK_HEADER_PATTERN.match(line)
            if match:
                current_new_line = int(match.group(1))
                in_hunk = True
                continue

            if not in_hunk:
                continue

            if line.startswith("+") or line.startswith(" "):
                if current_new_line == line_number:
                    return True
                current_new_line += 1
            elif line.startswith("-"):
                # Line deleted from old version; does not increment new line counter
                continue
            elif line.startswith("\\"):
                # No newline marker
                continue

        return False

    @classmethod
    def format_finding_body(cls, finding: ConsensusFinding) -> str:
        """Format individual finding into GitHub Markdown."""
        conf_pct = (
            int(round(finding.confidence * 100))
            if finding.confidence is not None
            else 0
        )
        cat_str = finding.category.upper() if finding.category else "GENERAL"

        body = (
            f"### [{cat_str}] {finding.title}\n\n"
            f"**Severity:** `{finding.severity.upper()}` | **Confidence:** `{conf_pct}%`\n\n"
            f"**Reason:**\n{finding.reason}\n\n"
            f"**Evidence:**\n{finding.evidence}\n\n"
            f"**Recommendation:**\n{finding.recommendation}"
        )

        if finding.suggested_fix:
            body += f"\n\n**Suggested Fix:**\n```\n{finding.suggested_fix}\n```"

        return body

    @classmethod
    def format_review_body(
        cls,
        consensus_result: ConsensusReviewResult,
        unmapped_findings: List[ConsensusFinding],
    ) -> str:
        """Construct overall review summary markdown for the GitHub PR review."""
        if not consensus_result.findings or len(consensus_result.findings) == 0:
            return (
                "## PRify Automated Review Summary\n\n"
                "✅ **PRify review completed.** No actionable issues were identified in this Pull Request."
            )

        # Calculate severity breakdown
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in consensus_result.findings:
            sev_key = f.severity.upper()
            if sev_key in severity_counts:
                severity_counts[sev_key] += 1
            else:
                severity_counts["LOW"] += 1

        total_count = len(consensus_result.findings)
        inline_count = total_count - len(unmapped_findings)

        parts = [
            "## PRify Automated Review Summary\n",
            f"{consensus_result.summary}\n",
            "### 📊 Findings Overview",
            f"- **Total Findings:** {total_count}",
            f"- **Inline Comments Posted:** {inline_count}",
            f"- **Summary Fallbacks:** {len(unmapped_findings)}\n",
            "#### Severity Breakdown",
            f"- **Critical:** {severity_counts['CRITICAL']}",
            f"- **High:** {severity_counts['HIGH']}",
            f"- **Medium:** {severity_counts['MEDIUM']}",
            f"- **Low:** {severity_counts['LOW']}\n",
        ]

        if unmapped_findings:
            parts.append("### 📌 Additional Findings (File / Global Context)")
            for idx, finding in enumerate(unmapped_findings, 1):
                line_str = f":{finding.line_number}" if finding.line_number else ""
                file_str = (
                    f"`{finding.file_path}{line_str}`"
                    if finding.file_path
                    else "`Repository Scope`"
                )
                formatted_finding = cls.format_finding_body(finding)
                parts.append(
                    f"#### Finding #{idx}: {finding.title} ({file_str})\n{formatted_finding}\n"
                )

        return "\n".join(parts)

    @classmethod
    def format_github_review_payload(
        cls, consensus_result: ConsensusReviewResult, changed_files: List[ChangedFile]
    ) -> Dict[str, Any]:
        """
        Parses findings, maps valid inline line numbers to RIGHT-side patch lines,
        falls back unmapped findings to the review body, and returns the GitHub review payload.
        """
        # Map changed files by filename
        files_map: Dict[str, ChangedFile] = {cf.filename: cf for cf in changed_files}

        inline_comments: List[Dict[str, Any]] = []
        unmapped_findings: List[ConsensusFinding] = []

        if consensus_result and consensus_result.findings:
            for finding in consensus_result.findings:
                file_path = finding.file_path
                line_num = finding.line_number

                # Check if file exists in diff patch
                cf = files_map.get(file_path) if file_path else None
                if (
                    cf
                    and cf.patch
                    and line_num
                    and cls.is_line_in_diff(cf.patch, line_num)
                ):
                    inline_comments.append(
                        {
                            "path": file_path,
                            "line": line_num,
                            "side": "RIGHT",
                            "body": cls.format_finding_body(finding),
                        }
                    )
                else:
                    # Fallback to summary body
                    unmapped_findings.append(finding)

        body = cls.format_review_body(consensus_result, unmapped_findings)

        return {"body": body, "event": "COMMENT", "comments": inline_comments}
