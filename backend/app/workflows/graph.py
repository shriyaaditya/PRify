from langgraph.graph import StateGraph
from pydantic import BaseModel

class GraphState(BaseModel):
    pr_url: str
    diff: str
    reviews: list[str]
    consensus: str

def build_workflow():
    workflow = StateGraph(GraphState)
    # Add nodes and edges here
    return workflow

app_graph = build_workflow()
