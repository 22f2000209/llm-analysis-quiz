"""
Dependency installer tool using uv (from someonesproject2).
"""

from langchain_core.tools import tool
from typing import List
import subprocess

@tool
def add_dependencies(dependencies: List[str]) -> str:
    """
    Install Python packages dynamically using uv.
    
    This allows the agent to install packages as needed for different tasks.
    Uses 'uv add' which works with uv-managed environments.
    
    Parameters
    ----------
    dependencies : List[str]
        List of package names to install.
        Example: ["pandas", "numpy", "matplotlib"]
    
    Returns
    -------
    str
        Success or error message
    """
    print(f"\n[DEPENDENCIES] Installing: {', '.join(dependencies)}")
    
    try:
        subprocess.check_call(
            ["uv", "add"] + dependencies,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"[DEPENDENCIES] ✓ Successfully installed: {', '.join(dependencies)}")
        return f"Successfully installed dependencies: {', '.join(dependencies)}"
    
    except subprocess.CalledProcessError as e:
        error_msg = (
            f"Dependency installation failed.\n"
            f"Exit code: {e.returncode}\n"
            f"Error: {e.stderr or 'No error output.'}"
        )
        print(f"[DEPENDENCIES] ✗ Installation failed")
        print(f"[DEPENDENCIES] Error: {error_msg}")
        return error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error while installing dependencies: {e}"
        print(f"[DEPENDENCIES] ✗ Exception: {error_msg}")
        return error_msg

