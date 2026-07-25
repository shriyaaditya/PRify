import logging
import time
from typing import List, Tuple

# Import agents to ensure they are registered
from app.agents.base.context import ReviewContext
from app.agents.base.registry import AgentRegistry
from app.agents.base.result import AgentExecution, AgentResult
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the execution of review agents.
    """

    def __init__(self, active_agents: List[str] = None):
        """
        Initialize the orchestrator with a list of active agent names.
        If active_agents is None, all registered agents will be run.
        """
        self.active_agents = active_agents
        # Instantiate the shared LLM Provider
        self.llm_provider = OpenAIProvider()

    async def execute(
        self, context: ReviewContext
    ) -> Tuple[List[AgentResult], List[AgentExecution]]:
        """
        Execute the configured review agents sequentially and gather results and metadata.
        """
        results: List[AgentResult] = []
        executions: List[AgentExecution] = []

        all_classes = AgentRegistry.get_all_agent_classes()
        agents_to_run = (
            self.active_agents
            if self.active_agents is not None
            else list(all_classes.keys())
        )

        for agent_name in agents_to_run:
            if agent_name not in all_classes:
                logger.warning(
                    f"Agent '{agent_name}' is configured to run but not registered."
                )
                continue

            agent_class = all_classes[agent_name]

            # Simple Dependency Injection
            try:
                # If it's an agent that requires an LLMProvider, inject it
                if agent_name in (
                    "ArchitectureAgent",
                    "SecurityAgent",
                    "PerformanceAgent",
                    "TestingAgent",
                ):
                    agent = agent_class(llm_provider=self.llm_provider)
                else:
                    agent = agent_class()
            except Exception as e:
                logger.error(f"Failed to instantiate agent '{agent_name}': {e}")
                executions.append(
                    AgentExecution(
                        agent_name=agent_name,
                        start_time=time.time(),
                        duration_ms=0,
                        status="failed",
                        errors=[f"Instantiation error: {str(e)}"],
                    )
                )
                continue

            start_time = time.time()
            logger.info(f"Starting execution of agent: {agent.name}")

            try:
                result = await agent.review(context)
                duration_ms = (time.time() - start_time) * 1000

                results.append(result)
                executions.append(
                    AgentExecution(
                        agent_name=agent.name,
                        start_time=start_time,
                        duration_ms=duration_ms,
                        status="success",
                    )
                )
                logger.info(
                    f"Agent '{agent.name}' completed in {duration_ms:.2f}ms with {len(result.findings)} findings."
                )
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    f"Agent '{agent.name}' failed after {duration_ms:.2f}ms: {e}"
                )
                executions.append(
                    AgentExecution(
                        agent_name=agent.name,
                        start_time=start_time,
                        duration_ms=duration_ms,
                        status="failed",
                        errors=[str(e)],
                    )
                )

        return results, executions
