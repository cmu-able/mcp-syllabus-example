"""Utility functions for the orchestrator."""
import sys
from pathlib import Path

from rich.console import Console

console = Console()


def expand_pdf_paths(paths: tuple[str, ...]) -> list[str]:
    """Expand paths to include all PDFs in directories.
    
    Args:
        paths: Tuple of file paths and/or directory paths
        
    Returns:
        List of PDF file paths with directories expanded
        
    Raises:
        SystemExit: If a directory contains no PDF files
    """
    pdf_files: list[str] = []
    
    for path_str in paths:
        path = Path(path_str)
        
        if path.is_file():
            # It's a file, add it directly
            pdf_files.append(path_str)
        elif path.is_dir():
            # It's a directory, find all PDFs
            pdfs_in_dir = sorted(path.glob("*.pdf"))
            
            if not pdfs_in_dir:
                console.print(
                    f"[red]Error:[/red] Directory '{path_str}' contains no PDF files.",
                    file=sys.stderr
                )
                raise SystemExit(1)
            
            pdf_files.extend(str(p) for p in pdfs_in_dir)
        else:
            console.print(
                f"[red]Error:[/red] Path '{path_str}' does not exist.",
                file=sys.stderr
            )
            raise SystemExit(1)
    
    return pdf_files
