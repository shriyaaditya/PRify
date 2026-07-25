import logging
from typing import Any, Dict

from app.agents.consensus.agent import ConsensusAgent
from app.agents.orchestrator.mapper import ContextMapper
from app.llm.openai_provider import OpenAIProvider
from app.workflows.github_review.state import GitHubReviewState

logger = logging.getLogger(__name__)


async def run_consensus(state: GitHubReviewState) -> Dict[str, Any]:
    """
    LangGraph node to execute the Consensus Agent after all specialist agents have completed.
    Consolidates specialist findings into a unified, high-quality consensus result.
    """
    logger.info("Executing Consensus Agent...")

    try:
        # 1. Map state to immutable ReviewContext
        context = ContextMapper.map_from_state(state)

        # 2. Instantiate LLM provider & ConsensusAgent
        llm_provider = OpenAIProvider()
        consensus_agent = ConsensusAgent(llm_provider=llm_provider)

        # 3. Consolidate specialist agent results
        consensus_result = await consensus_agent.consolidate(
            agent_results=state.agent_results, context=context
        )

        logger.info(
            f"Consensus Agent execution complete. "
            f"Consolidated into {len(consensus_result.findings)} final findings."
        )

        # 4. Return state update
        return {"consensus_result": consensus_result}

    except Exception as e:
        logger.error(f"Failed to execute Consensus Agent: {e}", exc_info=True)
        return {"errors": [f"Consensus Agent execution failed: {str(e)}"]}
