"""
Enhanced POST request tool with retry logic and time tracking.
Based on someonesproject2 with improvements from your project.
"""

from langchain_core.tools import tool
import requests
import json
import time
from typing import Any, Dict, Optional

# Track submission history
_submission_history = []
_start_time = None

def reset_submission_tracking():
    """Reset submission tracking for new quiz chain."""
    global _submission_history, _start_time
    _submission_history = []
    _start_time = time.time()

@tool
def post_request(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Any:
    """
    Send an HTTP POST request to submit an answer with enhanced tracking.

    This function submits quiz answers and tracks submission history for retry logic.
    It respects the 3-minute time limit and prevents resubmission after timeout.

    REMEMBER: This is a blocking function so it may take a while to return. 
    Wait for the response.

    Args:
        url (str): The endpoint to send the POST request to.
        payload (Dict[str, Any]): The JSON-serializable request body.
            Should contain: email, secret, url, answer
        headers (Optional[Dict[str, str]]): Optional HTTP headers.

    Returns:
        Any: The response body with next URL if available.
            {
                "correct": bool,
                "url": str (next question URL, if any),
                "reason": str (if incorrect),
                "delay": float (elapsed time)
            }
    """
    global _submission_history, _start_time
    
    if _start_time is None:
        _start_time = time.time()
    
    elapsed = time.time() - _start_time
    
    headers = headers or {"Content-Type": "application/json"}
    
    print(f"\n[SUBMIT] Submitting answer to: {url}")
    print(f"[SUBMIT] Payload: {json.dumps(payload, indent=2)}")
    print(f"[SUBMIT] Elapsed time: {elapsed:.1f}s / 180s")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        delay = data.get("delay", elapsed)
        correct = data.get("correct", False)
        next_url = data.get("url")
        reason = data.get("reason", "")
        
        # Track submission
        _submission_history.append({
            "url": payload.get("url"),
            "answer": payload.get("answer"),
            "correct": correct,
            "delay": delay,
            "timestamp": time.time()
        })
        
        # Build response
        result = {
            "correct": correct,
            "delay": delay,
            "reason": reason
        }
        
        # Handle next URL based on correctness and time limit
        if correct:
            print(f"[SUBMIT] ✓ Correct answer!")
            if next_url:
                result["url"] = next_url
                print(f"[SUBMIT] Next question: {next_url}")
            else:
                print(f"[SUBMIT] ✓ Quiz chain completed!")
        else:
            print(f"[SUBMIT] ✗ Wrong answer")
            if reason:
                print(f"[SUBMIT] Reason: {reason}")
            
            # Only provide next URL if within time limit
            if delay < 180 and next_url:
                # Allow retry by not including next URL
                # Agent will retry current question
                print(f"[SUBMIT] Time remaining: {180 - delay:.1f}s - can retry")
            elif delay >= 180:
                # Time limit exceeded - move to next if available
                if next_url:
                    result["url"] = next_url
                    print(f"[SUBMIT] Time limit exceeded - moving to next question")
                else:
                    print(f"[SUBMIT] Time limit exceeded - quiz ended")
        
        print(f"[SUBMIT] Response: {json.dumps(result, indent=2)}")
        return result
        
    except requests.HTTPError as e:
        err_resp = e.response
        try:
            err_data = err_resp.json()
        except ValueError:
            err_data = err_resp.text
        
        print(f"[SUBMIT] ✗ HTTP Error: {err_data}")
        return {"error": err_data, "correct": False}
    
    except Exception as e:
        error_msg = str(e)
        print(f"[SUBMIT] ✗ Exception: {error_msg}")
        return {"error": error_msg, "correct": False}
