import logging

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.agents.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider.
    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.llm = ChatOpenAI(model=self.model_name, temperature=0.0)

    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        """
        Uses LangChain's structured output capabilities to ensure the LLM
        returns a response matching the Pydantic schema.
        """
        llm_with_temp = ChatOpenAI(model=self.model_name, temperature=temperature)
        structured_llm = llm_with_temp.with_structured_output(response_model)

        messages = [("system", system_prompt), ("user", user_prompt)]

        logger.info(f"Invoking {self.model_name} for structured response.")
        response = await structured_llm.ainvoke(messages)
        return response
