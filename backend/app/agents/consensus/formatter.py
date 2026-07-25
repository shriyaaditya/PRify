from typing import List

from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult


class ConsensusContextFormatter:
    """
    Formats specialist AgentResults and minimal ReviewContext into a compact string representation
    for evaluation and consolidation by the Consensus Agent.
    """

    @classmethod
    def format_for_consensus(
        cls,
        agent_results: List[AgentResult],
        context: ReviewContext,
        max_patch_chars_per_file: int = 1500,
    ) -> str:
        formatted_parts = []

        # 1. PR Metadata
        formatted_parts.append("### Pull Request Context")
        formatted_parts.append(f"PR Title: {context.pull_request.title}")
        if context.pull_request.description:
            formatted_parts.append(
                f"PR Description: {context.pull_request.description}"
            )

        # 2. Changed Code Files (Minimal diff for evidence verification)
        formatted_parts.append(
            "\n### Changed Files (Diff Snippets for Evidence Verification)"
        )
        if context.changed_files:
            for cf in context.changed_files[:10]:
                status_str = getattr(cf, "status", "modified")
                formatted_parts.append(
                    f"--- File: {cf.filename} (Status: {status_str}) ---"
                )
                if hasattr(cf, "patch") and cf.patch:
                    patch = (
                        cf.patch[:max_patch_chars_per_file] + "\n...[truncated]"
                        if len(cf.patch) > max_patch_chars_per_file
                        else cf.patch
                    )
                    formatted_parts.append(f"Patch:\n```\n{patch}\n```")
        else:
            formatted_parts.append("No changed files provided in context.")

        # 3. Specialist Agent Results
        formatted_parts.append("\n### Specialist Agent Findings")
        if not agent_results:
            formatted_parts.append("No specialist agent results were provided.")
        else:
            total_findings = sum(len(ar.findings) for ar in agent_results)
            formatted_parts.append(
                f"Total Specialist Findings Received: {total_findings}\n"
            )

            for ar in agent_results:
                formatted_parts.append(f"=== Agent: {ar.agent_name} ===")
                formatted_parts.append(f"Agent Summary: {ar.summary}")
                if not ar.findings:
                    formatted_parts.append("Findings: None\n")
                    continue

                formatted_parts.append(f"Findings Count: {len(ar.findings)}")
                for idx, finding in enumerate(ar.findings, 1):
                    line_str = f":{finding.line_number}" if finding.line_number else ""
                    formatted_parts.append(
                        f"\n  [{idx}] Title: {finding.title}\n"
                        f"      Category: {finding.category}\n"
                        f"      Severity: {finding.severity}\n"
                        f"      Confidence: {finding.confidence}\n"
                        f"      File: {finding.file_path}{line_str}\n"
                        f"      Description: {finding.description}\n"
                        f"      Recommendation: {finding.recommendation}\n"
                        f"      Evidence: {finding.evidence}"
                    )
                formatted_parts.append("")

        return "\n".join(formatted_parts)
