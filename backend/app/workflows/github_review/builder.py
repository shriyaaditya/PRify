from langgraph.graph import END, START, StateGraph

from app.workflows.github_review.nodes.analyze_semgrep import analyze_semgrep
from app.workflows.github_review.nodes.fetch_changed_files import fetch_changed_files
from app.workflows.github_review.nodes.finish import finish
from app.workflows.github_review.nodes.index_repository import index_repository
from app.workflows.github_review.nodes.parse_repository import parse_repository
from app.workflows.github_review.nodes.publish_review import publish_review
from app.workflows.github_review.nodes.retrieve_repository_context import (
    retrieve_repository_context,
)
from app.workflows.github_review.nodes.run_agents import run_agents
from app.workflows.github_review.nodes.run_consensus import run_consensus
from app.workflows.github_review.nodes.sync_pull_request import sync_pull_request
from app.workflows.github_review.nodes.sync_repository import sync_repository
from app.workflows.github_review.nodes.validate_event import validate_event
from app.workflows.github_review.state import GitHubReviewState


def build_graph() -> StateGraph:
    """
    Build the GitHub Review LangGraph workflow.
    """
    builder = StateGraph(GitHubReviewState)

    # Add Nodes
    builder.add_node("validate_event", validate_event)
    builder.add_node("sync_repository", sync_repository)
    builder.add_node("sync_pull_request", sync_pull_request)
    builder.add_node("fetch_changed_files", fetch_changed_files)
    builder.add_node("parse_repository", parse_repository)
    builder.add_node("analyze_semgrep", analyze_semgrep)
    builder.add_node("index_repository", index_repository)
    builder.add_node("retrieve_repository_context", retrieve_repository_context)
    builder.add_node("run_agents", run_agents)
    builder.add_node("run_consensus", run_consensus)
    builder.add_node("publish_review", publish_review)
    builder.add_node("finish", finish)

    # Define Edges
    builder.add_edge(START, "validate_event")
    builder.add_edge("validate_event", "sync_repository")
    builder.add_edge("sync_repository", "sync_pull_request")
    builder.add_edge("sync_pull_request", "fetch_changed_files")
    builder.add_edge("fetch_changed_files", "parse_repository")
    builder.add_edge("parse_repository", "analyze_semgrep")
    builder.add_edge("analyze_semgrep", "index_repository")
    builder.add_edge("index_repository", "retrieve_repository_context")
    builder.add_edge("retrieve_repository_context", "run_agents")
    builder.add_edge("run_agents", "run_consensus")
    builder.add_edge("run_consensus", "publish_review")
    builder.add_edge("publish_review", "finish")
    builder.add_edge("finish", END)

    return builder
