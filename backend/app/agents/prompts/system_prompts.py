import os


def load_prompt(prompt_name: str) -> str:
    """
    Loads a markdown prompt from the prompts directory.
    Assumes prompts are stored in app/agents/prompts/{prompt_name}.md
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, f"{prompt_name}.md")

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
