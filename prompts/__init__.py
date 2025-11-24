"""Utility functions for loading prompt text files."""
from pathlib import Path
import typing as t
import os


def load_prompt(prompt_name: str, prompts_dir: t.Optional[str] = None) -> str:
    """
    Load a prompt from a text file.
    
    Args:
        prompt_name: Name of the prompt file (without .txt extension)
        prompts_dir: Optional custom path to prompts directory. 
                    Defaults to this module's parent directory.
    
    Returns:
        The content of the prompt file as a string.
        
    Raises:
        FileNotFoundError: If the prompt file doesn't exist.
        IOError: If there's an error reading the file.
    """
    # Default to prompts directory
    if prompts_dir is None:
        # Get the path to the prompts directory
        current_file = Path(__file__).resolve()
        prompts_dir = current_file.parent
    
    prompt_file = Path(prompts_dir) / f"{prompt_name}.txt"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        raise IOError(f"Error reading prompt file {prompt_file}: {e}")