from typing import Type, Dict, List
from app.agents.base.agent import BaseReviewAgent

class AgentRegistry:
    """
    Registry for loading and storing available review agents.
    Stores agent classes rather than instances to enable dependency injection.
    """
    _agents: Dict[str, Type[BaseReviewAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Type[BaseReviewAgent]) -> None:
        """Register an agent class under a specific name."""
        cls._agents[name] = agent_class

    @classmethod
    def get_agent_class(cls, name: str) -> Type[BaseReviewAgent]:
        """Retrieve an agent class by name."""
        if name not in cls._agents:
            raise ValueError(f"Agent '{name}' not found in registry.")
        return cls._agents[name]

    @classmethod
    def get_all_agent_classes(cls) -> Dict[str, Type[BaseReviewAgent]]:
        """Retrieve all registered agent classes."""
        return cls._agents.copy()

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (useful for testing)."""
        cls._agents.clear()
