from app.agents.base.agent import BaseReviewAgent
from app.agents.base.context import ReviewContext
from app.agents.base.result import AgentResult, Finding
from app.agents.base.registry import AgentRegistry

class PlaceholderAgent(BaseReviewAgent):
    """
    A lightweight placeholder agent that returns dummy findings without LLM calls.
    Used for end-to-end framework validation.
    """

    @property
    def name(self) -> str:
        return "PlaceholderAgent"

    async def review(self, context: ReviewContext) -> AgentResult:
        finding = Finding(
            title="Dummy Finding from Placeholder",
            description=f"Analyzed {len(context.changed_files)} changed files and found nothing of consequence.",
            severity="info",
            confidence=1.0,
            recommendation="Keep up the good work!",
            file_path="N/A",
            category="general"
        )
        
        return AgentResult(
            agent_name=self.name,
            summary="Placeholder agent completed successfully.",
            findings=[finding]
        )

# Register the class
AgentRegistry.register("placeholder", PlaceholderAgent)
