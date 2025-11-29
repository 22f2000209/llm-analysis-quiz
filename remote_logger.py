"""
Remote logging utility for Hugging Face Spaces
Sends logs to GitHub Gist (permanent, searchable storage)
"""

import requests
import os
from datetime import datetime

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def upload_to_github_gist(content, description="Quiz Solver Log"):
    """Upload log content to GitHub Gist"""
    if not GITHUB_TOKEN:
        print("[LOGGER] No GITHUB_TOKEN found, skipping remote logging")
        return None
    
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'quiz_logs_{timestamp}.txt'
        
        data = {
            'description': description,
            'public': False,  # Private gist
            'files': {
                filename: {
                    'content': content
                }
            }
        }
        
        response = requests.post('https://api.github.com/gists', json=data, headers=headers)
        
        if response.status_code == 201:
            gist_url = response.json().get('html_url')
            print(f"[LOGGER] ✓ Log uploaded to: {gist_url}")
            return gist_url
        else:
            print(f"[LOGGER] ✗ Failed to upload: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[LOGGER] ✗ Error uploading to Gist: {e}")
        return None

def log_question_result(question_num, time_taken, status, answer_preview):
    """Log individual question result"""
    content = f"""Question {question_num} Result
{'=' * 50}
Time: {time_taken}s
Status: {status}
Answer Preview: {answer_preview[:200]}...
Timestamp: {datetime.now()}
"""
    upload_to_github_gist(content, f"Q{question_num} Result")

def log_session_summary(total_questions, total_time, success_rate, details=""):
    """Log final session summary"""
    content = f"""Quiz Session Summary
{'=' * 50}
Total Questions: {total_questions}
Total Time: {total_time}s
Success Rate: {success_rate}%
Completed: {datetime.now()}

Details:
{details}
"""
    upload_to_github_gist(content, "Session Summary")
