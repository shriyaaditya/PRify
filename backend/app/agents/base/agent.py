from abc import ABC, abstractmethod
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult

class BaseReviewAgent(ABC):
    """
    Abstract base class for all review agents.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the agent."""
        pass

    @abstractmethod
    async def review(self, context: ReviewContext) -> AgentResult:
        """
        Execute the review logic using the provided context.
        """
        pass
