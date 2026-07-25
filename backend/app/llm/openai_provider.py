import os
from typing import Any, Dict, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from app.llm.provider import LLMProvider, LLMMessage, LLMResponse

class OpenAIProvider(LLMProvider):
    """
    OpenAI implementation of the LLMProvider using LangChain.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

    def _convert_messages(self, messages: List[LLMMessage]) -> List[BaseMessage]:
        lc_messages = []
        for msg in messages:
            if msg.role == "system":
                lc_messages.append(SystemMessage(content=msg.content))
            elif msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
            else:
                raise ValueError(f"Unsupported role: {msg.role}")
        return lc_messages

    async def generate(
        self,
        messages: List[LLMMessage],
        model: str = "gpt-4o",
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        model_kwargs = {}
        if response_format:
            model_kwargs["response_format"] = response_format

        llm = ChatOpenAI(
            model=model,
            api_key=self.api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs,
        )

        lc_messages = self._convert_messages(messages)
        response = await llm.ainvoke(lc_messages)
        
        # Extract token usage if available
        token_usage = {}
        if hasattr(response, "response_metadata") and response.response_metadata:
            token_usage_meta = response.response_metadata.get("token_usage", {})
            token_usage = {
                "prompt_tokens": token_usage_meta.get("prompt_tokens", 0),
                "completion_tokens": token_usage_meta.get("completion_tokens", 0),
                "total_tokens": token_usage_meta.get("total_tokens", 0),
            }

        return LLMResponse(
            content=response.content,
            token_usage=token_usage,
            cost=None, # LangChain's ainvoke doesn't give cost directly by default without callback
            model_name=model
        )
