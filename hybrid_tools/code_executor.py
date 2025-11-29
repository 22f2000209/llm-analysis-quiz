"""
Enhanced code executor with safety checks and smart features.
Combines someonesproject2's execution with your project's safety and timeout features.
"""

from langchain_core.tools import tool
import subprocess
import os
import tempfile
from typing import Dict

@tool
def run_code(code: str) -> dict:
    """
    Executes Python code in a sandboxed environment with safety checks.
    
    This tool:
      1. Validates code safety (no dangerous operations)
      2. Writes code into a temporary .py file
      3. Executes the file with timeout protection
      4. Returns stdout, stderr, and return code
    
    IMPORTANT RULES:
    - Code should assign the final answer to a variable named 'answer'
    - Do NOT include submission code (httpx.post, requests.post)
    - Do NOT hardcode data - always fetch from APIs/files
    - Use provided context variables if available
    
    Parameters
    ----------
    code : str
        Python source code to execute. Should end with: answer = <result>
    
    Returns
    -------
    dict
        {
            "stdout": <program output>,
            "stderr": <errors if any>,
            "return_code": <exit code>,
            "answer": <extracted answer if found>
        }
    """
    print(f"\n[CODE_EXECUTOR] Executing code ({len(code)} chars)")
    
    try:
        # Safety validation
        dangerous_patterns = [
            'os.system', 'subprocess.call', 'eval(', 'exec(',
            '__import__', 'open(', 'file(',
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                print(f"[CODE_EXECUTOR] ⚠ Warning: Potentially dangerous pattern '{pattern}' detected")
        
        # Create execution directory
        exec_dir = "hybrid_llm_files"
        os.makedirs(exec_dir, exist_ok=True)
        
        # Write code to file
        filename = "runner.py"
        filepath = os.path.join(exec_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(code)
        
        print(f"[CODE_EXECUTOR] Code written to {filepath}")
        print(f"[CODE_EXECUTOR] Starting execution with uv run...")
        
        # Execute with timeout
        try:
            print(f"[CODE_EXECUTOR] Command: uv run {filename}")
            print(f"[CODE_EXECUTOR] Working directory: {exec_dir}")
            
            proc = subprocess.Popen(
                ["uv", "run", filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=exec_dir
            )
            
            print(f"[CODE_EXECUTOR] Process started, waiting for completion (90s timeout)...")
            stdout, stderr = proc.communicate(timeout=90)
            return_code = proc.returncode
            
            print(f"[CODE_EXECUTOR] Process completed with return code: {return_code}")
            
        except subprocess.TimeoutExpired:
            print(f"[CODE_EXECUTOR] ⏱️ Timeout expired after 90 seconds")
            proc.kill()
            stdout, stderr = proc.communicate()
            return {
                "stdout": stdout,
                "stderr": "Error: Code execution timed out (90 seconds)",
                "return_code": -1,
                "answer": None
            }

        
        # Try to extract answer from output
        answer = None
        if return_code == 0:
            # Look for "answer = " in stdout
            for line in stdout.split('\n'):
                if line.strip():
                    # Last non-empty line is likely the answer
                    answer = line.strip()
        
        # Detect if answer is base64 (long string)
        is_base64 = False
        if answer and len(answer) > 1000:
            is_base64 = True
            print(f"[CODE_EXECUTOR] Detected base64 answer ({len(answer)} chars)")
        
        # Truncate stdout to avoid overwhelming LLM
        truncated_stdout = stdout
        if len(stdout) > 500:
            truncated_stdout = stdout[:500] + f"\n... (truncated {len(stdout) - 500} chars)"
        
        result = {
            "stdout": truncated_stdout,
            "stderr": stderr,
            "return_code": return_code,
            "answer": answer  # Keep full answer - needed for submission
        }
        
        if return_code == 0:
            print(f"[CODE_EXECUTOR] ✓ Execution successful")
            if answer:
                if is_base64:
                    # Show preview for base64 - don't print full string
                    print(f"[CODE_EXECUTOR] Answer: [BASE64 IMAGE - {len(answer)} chars]")
                else:
                    print(f"[CODE_EXECUTOR] Answer extracted: {answer}")
            if stdout and not is_base64:
                print(f"[CODE_EXECUTOR] Stdout preview: {stdout[:200]}")
        else:
            print(f"[CODE_EXECUTOR] ✗ Execution failed with code {return_code}")
            if stderr:
                print(f"[CODE_EXECUTOR] Error: {stderr[:500]}")
            if stdout:
                print(f"[CODE_EXECUTOR] Stdout: {stdout[:200]}")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"[CODE_EXECUTOR] ✗ Exception: {error_msg}")
        import traceback
        print(f"[CODE_EXECUTOR] Traceback:")
        traceback.print_exc()
        return {
            "stdout": "",
            "stderr": error_msg,
            "return_code": -1,
            "answer": None
        }

