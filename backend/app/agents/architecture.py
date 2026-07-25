import time
import json
import logging
from typing import Any, Dict

from app.agents.base.agent import BaseReviewAgent
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult, Finding
from app.agents.base.registry import agent_registry
from app.agents.llm.openai_provider import OpenAIProvider
from app.agents.prompts.system_prompts import load_prompt

logger = logging.getLogger(__name__)

class ArchitectureAgent(BaseReviewAgent):
    """
    Analyzes code changes against architectural guidelines and structural patterns.
    """
    
    def __init__(self):
        self.llm_provider = OpenAIProvider()
        self.system_prompt = load_prompt("architecture")

    @property
    def name(self) -> str:
        return "Architecture"

    async def review(self, context: ReviewContext) -> AgentResult:
        logger.info("Starting ArchitectureAgent review...")
        start_time = time.time()
        
        # Build user prompt with the context
        user_prompt = self._build_user_prompt(context)
        
        try:
            # Query LLM with structured output matching AgentResult
            response = await self.llm_provider.generate_structured_response(
                system_prompt=self.system_prompt,
                user_prompt=user_prompt,
                response_model=AgentResult
            )
            
            # Ensure the agent name is set correctly
            response.agent_name = self.name
            response.execution_time_ms = int((time.time() - start_time) * 1000)
            return response
            
        except Exception as e:
            logger.error(f"ArchitectureAgent failed: {str(e)}")
            return AgentResult(
                agent_name=self.name,
                summary="Agent encountered an error during execution.",
                findings=[],
                confidence=0.0,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def _build_user_prompt(self, context: ReviewContext) -> str:
        """Constructs the prompt containing the PR context and RAG documents."""
        prompt = f"Repository: {context.repository.full_name}\n"
        prompt += f"Pull Request: {context.pull_request.title}\n\n"
        
        prompt += "--- Architectural Context (from RAG) ---\n"
        for doc in context.retrieved_context:
            prompt += f"Source: {doc.get('source', 'Unknown')}\n"
            prompt += f"{doc.get('content', '')}\n\n"
            
        prompt += "--- Changed Files ---\n"
        for cf in context.changed_files:
            prompt += f"File: {cf.filename}\n"
            prompt += f"Status: {cf.status}\n"
            if cf.patch:
                prompt += f"Diff:\n{cf.patch}\n\n"
                
        prompt += "--- Extracted Symbols ---\n"
        for sym in context.symbol_tables:
            prompt += f"File: {sym.filepath} | Type: {sym.type} | Name: {sym.name} | Lines: {sym.start_line}-{sym.end_line}\n"
            
        prompt += "\nPlease analyze the changes based on the provided architectural context and identify any violations."
        return prompt

# Register the agent
agent_registry.register(ArchitectureAgent())
