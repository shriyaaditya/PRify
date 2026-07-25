from app.workflows.github_review.builder import build_graph

# Compile the graph once to be imported and reused globally
graph = build_graph().compile()
