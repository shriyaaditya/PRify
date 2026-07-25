from typing import Dict, Any
import logging

from app.workflows.github_review.state import GitHubReviewState
from app.agents.orchestrator.mapper import ContextMapper
from app.agents.orchestrator.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

async def run_agents(state: GitHubReviewState) -> Dict[str, Any]:
    """
    LangGraph node to execute the review agents.
    """
    logger.info("Executing review agents...")
    
    try:
        # 1. Map state to immutable ReviewContext
        context = ContextMapper.map_from_state(state)
        
        # 2. Initialize orchestrator (defaulting to all registered agents for now)
        orchestrator = AgentOrchestrator()
        
        # 3. Execute agents
        results, executions = await orchestrator.execute(context)
        
        logger.info(f"Agents execution complete. Collected {len(results)} results.")
        
        # 4. Return state updates
        # `agent_results` and `execution_metadata` are annotated with operator.add in the state,
        # so returning lists will append them.
        return {
            "agent_results": results,
            "execution_metadata": executions
        }
        
    except Exception as e:
        logger.error(f"Failed to execute agents: {e}", exc_info=True)
        return {
            "errors": [f"Agent execution failed: {str(e)}"]
        }
