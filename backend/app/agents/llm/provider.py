from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers (e.g., OpenAI, Claude, local models).
    """

    @abstractmethod
    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        """
        Generates a structured Pydantic response from the LLM.
        """
        pass
