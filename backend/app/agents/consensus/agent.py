import logging
import os
import time
from typing import List

from pydantic import ValidationError

from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult
from app.agents.consensus.formatter import ConsensusContextFormatter
from app.agents.consensus.models import ConsensusReviewResult
from app.agents.prompts.manager import PromptManager
from app.llm.provider import LLMMessage, LLMProvider

logger = logging.getLogger(__name__)


class ConsensusAgent:
    """
    Consensus Review Agent.
    Architecturally separate from BaseReviewAgent (contract: List[AgentResult] + ReviewContext -> ConsensusReviewResult).
    Consolidates, deduplicates, resolves conflicts, normalizes severity, and verifies findings
    produced by specialist review agents.
    """

    __test__ = False

    def __init__(self, llm_provider: LLMProvider, max_patch_chars_per_file: int = 1500):
        self.llm_provider = llm_provider
        self.max_patch_chars_per_file = max_patch_chars_per_file

        prompts_dir = os.path.dirname(__file__)
        self.prompt_manager = PromptManager(prompts_dir=prompts_dir)

    @property
    def name(self) -> str:
        return "ConsensusAgent"

    async def consolidate(
        self, agent_results: List[AgentResult], context: ReviewContext
    ) -> ConsensusReviewResult:
        start_time = time.time()

        # Calculate total input specialist findings
        input_findings_count = sum(len(ar.findings) for ar in agent_results)
        logger.info(
            f"ConsensusAgent starting consolidation for {len(agent_results)} agent results "
            f"containing {input_findings_count} total specialist findings."
        )

        # Quick path: if no specialist findings exist, return empty ConsensusReviewResult immediately
        if input_findings_count == 0:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                f"ConsensusAgent completed in {duration_ms:.2f}ms. "
                "No specialist findings to consolidate."
            )
            return ConsensusReviewResult(
                summary=(
                    "Consensus review complete. "
                    "No issues were flagged by specialist agents."
                ),
                findings=[],
            )

        # 1. Format Context & Agent Results
        formatted_context = ConsensusContextFormatter.format_for_consensus(
            agent_results=agent_results,
            context=context,
            max_patch_chars_per_file=self.max_patch_chars_per_file,
        )
        context_size = len(formatted_context)
        logger.info(
            f"Consensus context formatted. Total Size: {context_size} characters."
        )

        # 2. Render System Prompt
        try:
            system_prompt = self.prompt_manager.render(
                "prompt", formatted_context=formatted_context
            )
        except Exception as e:
            logger.error(f"Failed to render consensus prompt: {e}")
            return ConsensusReviewResult(
                summary="Failed to generate system prompt for Consensus Agent.",
                findings=[],
            )

        prompt_size = len(system_prompt)
        logger.info(
            f"Consensus system prompt rendered. Prompt Size: {prompt_size} characters."
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(
                role="user",
                content=(
                    "Please consolidate the specialist findings and return JSON "
                    "matching the ConsensusReviewResult schema."
                ),
            ),
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
                    response_format={"type": "json_object"},
                )

                tokens_used = response.token_usage.get("total_tokens", 0)
                logger.info(
                    f"LLM consensus response received. Tokens used: {tokens_used}"
                )

                # 4. Validate output
                consensus_result = ConsensusReviewResult.model_validate_json(
                    response.content
                )
                final_findings_count = len(consensus_result.findings)

                # Accurately derive telemetry metrics
                merged_findings_count = sum(
                    len(f.source_agents) - 1
                    for f in consensus_result.findings
                    if f.source_agents and len(f.source_agents) > 1
                )

                # Accounted input findings = total input findings assigned to output consensus findings
                accounted_input_findings = sum(
                    len(f.source_agents) if f.source_agents else 1
                    for f in consensus_result.findings
                )
                suppressed_findings_count = max(
                    0, input_findings_count - accounted_input_findings
                )

                duration_ms = (time.time() - start_time) * 1000
                logger.info(
                    f"ConsensusAgent completed in {duration_ms:.2f}ms. "
                    f"Prompt Size: {prompt_size} chars | Context Size: {context_size} chars | "
                    f"Tokens: {tokens_used} | Validation failures: {validation_failures} | "
                    f"Retries: {retry_attempts} | Input findings: {input_findings_count} | "
                    f"Final findings: {final_findings_count} | Merged findings: {merged_findings_count} | "
                    f"Suppressed findings: {suppressed_findings_count}"
                )

                return consensus_result

            except ValidationError as ve:
                validation_failures += 1
                logger.warning(
                    f"Consensus JSON validation failed on attempt {attempt + 1}: {ve}"
                )
                if attempt == max_retries:
                    logger.error(
                        "Max retries reached for Consensus Agent JSON validation. "
                        "Returning empty result."
                    )
                    return ConsensusReviewResult(
                        summary=(
                            "LLM returned malformed JSON that failed "
                            "ConsensusReviewResult validation."
                        ),
                        findings=[],
                    )
                else:
                    retry_attempts += 1
                    messages.append(
                        LLMMessage(role="assistant", content=response.content)
                    )
                    error_msg = (
                        f"Your response failed Pydantic validation: {ve}. "
                        "Please fix the JSON structure."
                    )
                    messages.append(LLMMessage(role="user", content=error_msg))

            except Exception as e:
                logger.error(f"Unexpected error during ConsensusAgent execution: {e}")
                return ConsensusReviewResult(
                    summary=f"Consensus execution failed: {str(e)}", findings=[]
                )

        return ConsensusReviewResult(summary="Consensus review failed.", findings=[])
