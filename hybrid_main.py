"""
Hybrid FastAPI Server - Minimal and Clean

Based on someonesproject2's design with compatibility for your existing setup.
"""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from hybrid_agent import run_agent
from dotenv import load_dotenv
import uvicorn
import os
import time
import sys
from datetime import datetime

load_dotenv()

# Setup timestamped logging
log_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"hybrid_logs_{log_timestamp}.txt"
log_file = open(log_filename, "w", buffering=1)  # Line buffered

# Tee class to write to both console and file
class Tee:
    def __init__(self, *files):
        self.files = files
    
    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()
    
    def flush(self):
        for f in self.files:
            f.flush()

# Redirect stdout and stderr to both console and log file
sys.stdout = Tee(sys.stdout, log_file)
sys.stderr = Tee(sys.stderr, log_file)

print(f"[LOGGING] Session logs will be saved to: {log_filename}")


EMAIL = os.getenv("TDS_EMAIL") or os.getenv("EMAIL")
SECRET = os.getenv("TDS_SECRET") or os.getenv("SECRET")

app = FastAPI(title="Hybrid Quiz Solver")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()


@app.get("/healthz")
def healthz():
    """Health check endpoint."""
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "version": "hybrid-v1.0"
    }


@app.post("/quiz")
async def quiz_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Main quiz endpoint (compatible with your existing setup).
    
    Accepts:
        {
            "url": "quiz-url",
            "email": "optional-email",
            "secret": "your-secret"
        }
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if not data:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    url = data.get("url")
    secret = data.get("secret")
    
    if not url or not secret:
        raise HTTPException(status_code=400, detail="Missing 'url' or 'secret'")
    
    if secret != SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    print(f"[SERVER] ✓ Verified secret, starting task...")
    background_tasks.add_task(run_agent, url)
    
    return JSONResponse(status_code=200, content={"status": "accepted", "message": "Started"})


@app.post("/solve")
async def solve_endpoint(request: Request, background_tasks: BackgroundTasks):
    """
    Alternative endpoint (compatible with someonesproject2).
    
    Accepts:
        {
            "url": "quiz-url",
            "email": "optional-email",
            "secret": "your-secret"
        }
    """
    # Same as /quiz endpoint
    return await quiz_endpoint(request, background_tasks)


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"Hybrid Quiz Solver Server")
    print(f"{'='*60}")
    print(f"Email: {EMAIL}")
    print(f"Secret: {'*' * len(SECRET) if SECRET else 'NOT SET'}")
    print(f"{'='*60}\n")
    
    # Disable uvicorn's default logging to avoid conflicts with our Tee redirection
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
