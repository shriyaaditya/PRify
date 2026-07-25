import os
import json
import logging
import time
from typing import Optional

from pydantic import ValidationError

from app.agents.base.agent import BaseReviewAgent
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult, Finding
from app.llm.provider import LLMProvider, LLMMessage
from app.agents.prompts.manager import PromptManager
from app.agents.security.formatter import SecurityContextFormatter
from app.agents.security.models import SecurityReviewResult

logger = logging.getLogger(__name__)

class SecurityAgent(BaseReviewAgent):
    """
    Security Review Agent.
    Pure reasoning component that detects potential security vulnerabilities in pull requests
    by combining code diffs, Tree-sitter symbols, Semgrep findings, and RAG security docs.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        min_confidence_threshold: float = 0.7,
        max_files_budget: int = 10,
        max_symbols_budget: int = 30,
        max_semgrep_budget: int = 20,
        max_docs_chars_budget: int = 4000
    ):
        self.llm_provider = llm_provider
        self.min_confidence_threshold = float(
            os.getenv("SECURITY_CONFIDENCE_THRESHOLD", min_confidence_threshold)
        )
        self.max_files_budget = max_files_budget
        self.max_symbols_budget = max_symbols_budget
        self.max_semgrep_budget = max_semgrep_budget
        self.max_docs_chars_budget = max_docs_chars_budget

        prompts_dir = os.path.dirname(__file__)
        self.prompt_manager = PromptManager(prompts_dir=prompts_dir)

    @property
    def name(self) -> str:
        return "SecurityAgent"

    async def review(self, context: ReviewContext) -> AgentResult:
        start_time = time.time()
        semgrep_count = len(context.semgrep_findings)
        logger.info(
            f"SecurityAgent starting review. Semgrep findings available: {semgrep_count}. Confidence threshold: {self.min_confidence_threshold}."
        )

        # 1. Format Context
        formatted_context = SecurityContextFormatter.format_for_security(
            context,
            max_files=self.max_files_budget,
            max_symbols=self.max_symbols_budget,
            max_semgrep_findings=self.max_semgrep_budget,
            max_docs_chars=self.max_docs_chars_budget
        )
        context_size = len(formatted_context)
        logger.info(f"Security context formatted. Total Size: {context_size} characters.")

        # 2. Render System Prompt
        try:
            system_prompt = self.prompt_manager.render("prompt", formatted_context=formatted_context)
        except Exception as e:
            logger.error(f"Failed to render security prompt: {e}")
            return AgentResult(agent_name=self.name, summary="Failed to generate system prompt.")

        prompt_size = len(system_prompt)
        logger.info(f"Security system prompt rendered. Prompt Size: {prompt_size} characters.")

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content="Please perform the security review and return JSON matching the SecurityReviewResult schema.")
        ]

        # 3. Call LLM with low temperature (0.0) and validation retries
        max_retries = 1
        validation_failures = 0
        retry_attempts = 0

        for attempt in range(max_retries + 1):
            try:
                response = await self.llm_provider.generate(
                    messages=messages,
                    model="gpt-4o",
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )

                tokens_used = response.token_usage.get("total_tokens", 0)
                logger.info(f"LLM security response received. Tokens used: {tokens_used}")

                # 4. Validate output
                sec_result = SecurityReviewResult.model_validate_json(response.content)
                raw_findings_count = len(sec_result.findings)
                logger.info(f"Security output validation successful. Raw findings: {raw_findings_count}")

                # 5. Filter findings by confidence threshold
                accepted_findings = []
                filtered_count = 0

                for finding in sec_result.findings:
                    if finding.confidence < self.min_confidence_threshold:
                        filtered_count += 1
                        logger.info(
                            f"Filtered out security finding '{finding.title}' due to low confidence ({finding.confidence} < {self.min_confidence_threshold})."
                        )
                        continue

                    evidence_parts = [f"Code: {finding.code_evidence}", f"Docs: {finding.docs_evidence}"]
                    if finding.semgrep_evidence:
                        evidence_parts.append(f"Semgrep: {finding.semgrep_evidence}")

                    evidence_str = "\n".join(evidence_parts)

                    accepted_findings.append(Finding(
                        title=finding.title,
                        description=f"{finding.summary}\n\nReason: {finding.reason}\n\nImpact: {finding.impact}",
                        severity=finding.severity.lower(),
                        confidence=finding.confidence,
                        recommendation=finding.recommendation,
                        file_path=finding.file_path,
                        line_number=finding.line_number,
                        category=f"security:{finding.category.lower()}",
                        evidence=evidence_str
                    ))

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"SecurityAgent completed in {duration_ms:.2f}ms. "
                    f"Prompt Size: {prompt_size} chars | Context Size: {context_size} chars | "
                    f"Semgrep processed: {semgrep_count} | Tokens: {tokens_used} | "
                    f"Validation failures: {validation_failures} | Retries: {retry_attempts} | "
                    f"Accepted findings: {len(accepted_findings)} | Filtered findings: {filtered_count}"
                )

                return AgentResult(
                    agent_name=self.name,
                    summary=sec_result.summary,
                    findings=accepted_findings
                )

            except ValidationError as ve:
                validation_failures += 1
                logger.warning(f"Security JSON validation failed on attempt {attempt + 1}: {ve}")
                if attempt == max_retries:
                    logger.error("Max retries reached for Security Agent JSON validation. Returning error result.")
                    return AgentResult(
                        agent_name=self.name,
                        summary="LLM returned malformed JSON that failed SecurityReviewResult validation."
                    )
                else:
                    retry_attempts += 1
                    messages.append(LLMMessage(role="assistant", content=response.content))
                    error_msg = f"Your response failed Pydantic validation: {ve}. Please fix the JSON structure."
                    messages.append(LLMMessage(role="user", content=error_msg))

            except Exception as e:
                logger.error(f"Unexpected error during SecurityAgent execution: {e}")
                return AgentResult(agent_name=self.name, summary=f"Security execution failed: {str(e)}")

        return AgentResult(agent_name=self.name, summary="Security review failed.")

# Register the class
from app.agents.base.registry import AgentRegistry
AgentRegistry.register("SecurityAgent", SecurityAgent)
