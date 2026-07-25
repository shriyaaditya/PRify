import os
from typing import Dict, Any

class PromptManager:
    """
    Manages loading, caching, and rendering of prompt templates.
    """
    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir
        self._cache: Dict[str, str] = {}

    def _load_prompt(self, name: str) -> str:
        """Load a prompt from the filesystem or cache."""
        if name in self._cache:
            return self._cache[name]
        
        file_path = os.path.join(self.prompts_dir, f"{name}.txt")
        if not os.path.exists(file_path):
            file_path = os.path.join(self.prompts_dir, f"{name}.md")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompt '{name}' not found in {self.prompts_dir}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        self._cache[name] = content
        return content

    def render(self, name: str, **kwargs: Any) -> str:
        """
        Load a prompt template and render it with the provided kwargs.
        Simple string formatting for now.
        """
        template = self._load_prompt(name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required parameter for prompt '{name}': {e}")
