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
from app.agents.testing.formatter import TestingContextFormatter
from app.agents.testing.models import TestingReviewResult

logger = logging.getLogger(__name__)

class TestingAgent(BaseReviewAgent):
    """
    Testing Review Agent.
    Pure reasoning component that identifies missing, insufficient, or poorly targeted tests for Pull Request changes
    by analyzing production code diffs, test file diffs, Tree-sitter symbols, and RAG test docs.
    """
    __test__ = False

    def __init__(
        self,
        llm_provider: LLMProvider,
        min_confidence_threshold: float = 0.7,
        max_files_budget: int = 10,
        max_symbols_budget: int = 30,
        max_docs_chars_budget: int = 4000
    ):
        self.llm_provider = llm_provider
        self.min_confidence_threshold = float(
            os.getenv("TESTING_CONFIDENCE_THRESHOLD", min_confidence_threshold)
        )
        self.max_files_budget = max_files_budget
        self.max_symbols_budget = max_symbols_budget
        self.max_docs_chars_budget = max_docs_chars_budget

        prompts_dir = os.path.dirname(__file__)
        self.prompt_manager = PromptManager(prompts_dir=prompts_dir)

    @property
    def name(self) -> str:
        return "TestingAgent"

    async def review(self, context: ReviewContext) -> AgentResult:
        start_time = time.time()
        logger.info(
            f"TestingAgent starting review. Confidence threshold: {self.min_confidence_threshold}."
        )

        # 1. Format Context
        formatted_context = TestingContextFormatter.format_for_testing(
            context,
            max_files=self.max_files_budget,
            max_symbols=self.max_symbols_budget,
            max_docs_chars=self.max_docs_chars_budget
        )
        context_size = len(formatted_context)
        logger.info(f"Testing context formatted. Total Size: {context_size} characters.")

        # 2. Render System Prompt
        try:
            system_prompt = self.prompt_manager.render("prompt", formatted_context=formatted_context)
        except Exception as e:
            logger.error(f"Failed to render testing prompt: {e}")
            return AgentResult(agent_name=self.name, summary="Failed to generate system prompt.")

        prompt_size = len(system_prompt)
        logger.info(f"Testing system prompt rendered. Prompt Size: {prompt_size} characters.")

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content="Please perform the testing review and return JSON matching the TestingReviewResult schema.")
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
                logger.info(f"LLM testing response received. Tokens used: {tokens_used}")

                # 4. Validate output
                test_result = TestingReviewResult.model_validate_json(response.content)
                raw_findings_count = len(test_result.findings)
                logger.info(f"Testing output validation successful. Raw findings: {raw_findings_count}")

                # 5. Filter findings by confidence threshold
                accepted_findings = []
                filtered_count = 0

                for finding in test_result.findings:
                    if finding.confidence < self.min_confidence_threshold:
                        filtered_count += 1
                        logger.info(
                            f"Filtered out testing finding '{finding.title}' due to low confidence ({finding.confidence} < {self.min_confidence_threshold})."
                        )
                        continue

                    evidence_parts = [f"Code: {finding.code_evidence}"]
                    if finding.test_evidence:
                        evidence_parts.append(f"Test Evidence: {finding.test_evidence}")
                    if finding.docs_evidence:
                        evidence_parts.append(f"Docs: {finding.docs_evidence}")

                    evidence_str = "\n".join(evidence_parts)

                    recommendation = finding.recommendation
                    if finding.suggested_test:
                        recommendation += f"\n\nSuggested Test Scenario:\n{finding.suggested_test}"

                    accepted_findings.append(Finding(
                        title=finding.title,
                        description=f"{finding.summary}\n\nReason: {finding.reason}\n\nImpact: {finding.impact}",
                        severity=finding.severity.lower(),
                        confidence=finding.confidence,
                        recommendation=recommendation,
                        file_path=finding.file_path,
                        line_number=finding.line_number,
                        category=f"testing:{finding.category.lower()}",
                        evidence=evidence_str
                    ))

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"TestingAgent completed in {duration_ms:.2f}ms. "
                    f"Prompt Size: {prompt_size} chars | Context Size: {context_size} chars | "
                    f"Tokens: {tokens_used} | Validation failures: {validation_failures} | "
                    f"Retries: {retry_attempts} | Accepted findings: {len(accepted_findings)} | "
                    f"Filtered findings: {filtered_count}"
                )

                return AgentResult(
                    agent_name=self.name,
                    summary=test_result.summary,
                    findings=accepted_findings
                )

            except ValidationError as ve:
                validation_failures += 1
                logger.warning(f"Testing JSON validation failed on attempt {attempt + 1}: {ve}")
                if attempt == max_retries:
                    logger.error("Max retries reached for Testing Agent JSON validation. Returning error result.")
                    return AgentResult(
                        agent_name=self.name,
                        summary="LLM returned malformed JSON that failed TestingReviewResult validation."
                    )
                else:
                    retry_attempts += 1
                    messages.append(LLMMessage(role="assistant", content=response.content))
                    error_msg = f"Your response failed Pydantic validation: {ve}. Please fix the JSON structure."
                    messages.append(LLMMessage(role="user", content=error_msg))

            except Exception as e:
                logger.error(f"Unexpected error during TestingAgent execution: {e}")
                return AgentResult(agent_name=self.name, summary=f"Testing execution failed: {str(e)}")

        return AgentResult(agent_name=self.name, summary="Testing review failed.")

# Register the class
from app.agents.base.registry import AgentRegistry
AgentRegistry.register("TestingAgent", TestingAgent)
