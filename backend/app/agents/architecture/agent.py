import os
import json
import logging
from typing import Optional

from pydantic import ValidationError

from app.agents.base.agent import BaseReviewAgent
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult, Finding
from app.llm.provider import LLMProvider, LLMMessage
from app.agents.prompts.manager import PromptManager
from app.agents.architecture.formatter import ContextFormatter
from app.agents.architecture.models import ArchitectureReviewResult

logger = logging.getLogger(__name__)

class ArchitectureAgent(BaseReviewAgent):
    """
    Architecture Review Agent.
    A pure reasoning component that analyzes pull requests for architectural violations using tree-sitter symbols and RAG docs.
    Operates strictly on the immutable ReviewContext without making direct external calls.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        min_confidence_threshold: float = 0.7,
        max_files_budget: int = 10,
        max_symbols_budget: int = 30,
        max_docs_chars_budget: int = 4000
    ):
        self.llm_provider = llm_provider
        self.min_confidence_threshold = float(os.getenv("ARCHITECTURE_CONFIDENCE_THRESHOLD", min_confidence_threshold))
        self.max_files_budget = max_files_budget
        self.max_symbols_budget = max_symbols_budget
        self.max_docs_chars_budget = max_docs_chars_budget
        
        prompts_dir = os.path.dirname(__file__)
        self.prompt_manager = PromptManager(prompts_dir=prompts_dir)

    @property
    def name(self) -> str:
        return "ArchitectureAgent"

    async def review(self, context: ReviewContext) -> AgentResult:
        logger.info(f"ArchitectureAgent starting review (Confidence Threshold: {self.min_confidence_threshold}).")
        
        # 1. Format Context preserving source identity & applying context budget
        formatted_context = ContextFormatter.format_for_architecture(
            context,
            max_files=self.max_files_budget,
            max_symbols=self.max_symbols_budget,
            max_docs_chars=self.max_docs_chars_budget
        )
        context_size = len(formatted_context)
        logger.info(f"Context formatted with budgets. Total Size: {context_size} characters.")
        
        # 2. Prepare Prompt
        try:
            system_prompt = self.prompt_manager.render("prompt", formatted_context=formatted_context)
        except Exception as e:
            logger.error(f"Failed to render architecture prompt: {e}")
            return AgentResult(agent_name=self.name, summary="Failed to generate system prompt.")
            
        prompt_size = len(system_prompt)
        logger.info(f"System prompt rendered. Total Prompt Size: {prompt_size} characters.")

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content="Please analyze the architectural health and return JSON matching the ArchitectureReviewResult schema.")
        ]
        
        # 3. Call LLM (Deterministic low temperature, with retry on validation failure)
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                response = await self.llm_provider.generate(
                    messages=messages,
                    model="gpt-4o",
                    temperature=0.0,  # Low temperature (0-0.2) for determinism
                    response_format={"type": "json_object"}
                )
                
                logger.info(f"LLM response received. Token Usage: {response.token_usage}")
                
                # 4. Validate output
                arch_result = ArchitectureReviewResult.model_validate_json(response.content)
                logger.info(f"Validation successful. Found {len(arch_result.findings)} raw findings.")
                
                # 5. Filter & Map to generic AgentResult based on confidence threshold
                generic_findings = []
                for finding in arch_result.findings:
                    if finding.confidence < self.min_confidence_threshold:
                        logger.info(
                            f"Filtering out finding '{finding.title}' due to low confidence ({finding.confidence} < {self.min_confidence_threshold})."
                        )
                        continue

                    evidence_str = f"Code Evidence: {finding.code_evidence}\nDocs Evidence: {finding.docs_evidence}"
                    generic_findings.append(Finding(
                        title=finding.title,
                        description=finding.reason,
                        severity=finding.severity.lower(),
                        confidence=finding.confidence,
                        recommendation=finding.recommendation,
                        file_path=finding.file_path,
                        line_number=finding.line_number,
                        category="architecture",
                        evidence=evidence_str
                    ))
                    
                logger.info(f"Final AgentResult constructed with {len(generic_findings)} high-confidence findings.")
                return AgentResult(
                    agent_name=self.name,
                    summary=arch_result.summary,
                    findings=generic_findings
                )

            except ValidationError as ve:
                logger.warning(f"JSON Validation failed on attempt {attempt + 1}: {ve}")
                if attempt == max_retries:
                    logger.error("Max retries reached for JSON validation. Returning empty AgentResult with error.")
                    return AgentResult(agent_name=self.name, summary="LLM returned malformed JSON that failed validation.")
                else:
                    messages.append(LLMMessage(role="assistant", content=response.content))
                    error_msg = f"Your previous response failed validation with error: {ve}. Please fix the JSON output structure."
                    messages.append(LLMMessage(role="user", content=error_msg))
                    
            except Exception as e:
                logger.error(f"Unexpected error during ArchitectureAgent execution: {e}")
                return AgentResult(agent_name=self.name, summary=f"Execution failed: {str(e)}")

        return AgentResult(agent_name=self.name, summary="Review failed.")

# Register the class
from app.agents.base.registry import AgentRegistry
AgentRegistry.register("ArchitectureAgent", ArchitectureAgent)
