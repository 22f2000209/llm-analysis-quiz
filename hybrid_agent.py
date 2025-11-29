"""
Hybrid LangGraph Agent - Best of Both Worlds

Combines:
- LangGraph architecture from someonesproject2
- Enhanced features from your project
"""

from langgraph.graph import StateGraph, END, START
from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from hybrid_tools import (
    get_rendered_html, run_code, post_request, download_file,
    add_dependencies, transcribe_audio, extract_context,
    analyze_image, create_visualization, create_chart_from_data
)
from typing import TypedDict, Annotated, List, Dict, Any
from langchain.chat_models import init_chat_model
from langgraph.graph.message import add_messages
import os
from dotenv import load_dotenv
import time

load_dotenv()

EMAIL = os.getenv("TDS_EMAIL") or os.getenv("EMAIL")
SECRET = os.getenv("TDS_SECRET") or os.getenv("SECRET")
RECURSION_LIMIT = 5000

# Global variables for log management
current_log_file = None
upload_thread = None
stop_upload_thread = False

def upload_current_log(reason="Progress"):
    """Upload current log file to GitHub Gist."""
    try:
        from remote_logger import upload_to_github_gist
        import glob
        
        # Find the most recent log file
        log_files = glob.glob("hybrid_logs_*.txt")
        if log_files:
            latest_log = max(log_files, key=os.path.getctime)
            with open(latest_log, 'r') as f:
                log_content = f.read()
            
            upload_to_github_gist(
                content=log_content,
                description=f"Quiz Solver {reason} - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
    except Exception:
        pass  # Silent fail

def periodic_upload_worker():
    """Background worker that uploads logs every 5 minutes."""
    global stop_upload_thread
    import threading
    
    while not stop_upload_thread:
        # Wait 5 minutes (300 seconds)
        for _ in range(300):
            if stop_upload_thread:
                return
            time.sleep(1)
        
        # Upload if still running
        if not stop_upload_thread:
            upload_current_log("Progress Update")

def start_periodic_uploads():
    """Start background thread for periodic uploads."""
    global upload_thread, stop_upload_thread
    import threading
    
    stop_upload_thread = False
    upload_thread = threading.Thread(target=periodic_upload_worker, daemon=True)
    upload_thread.start()

def stop_periodic_uploads():
    """Stop background upload thread."""
    global stop_upload_thread
    stop_upload_thread = True

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully by uploading logs."""
    print("\n[AGENT] ⚠️ Interrupted by user, uploading logs...")
    stop_periodic_uploads()
    upload_current_log("Interrupted")
    print("[AGENT] ✓ Logs uploaded, exiting...")
    import sys
    sys.exit(0)

# Register signal handler for Ctrl+C
import signal
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# -------------------------------------------------
# ENHANCED STATE
# -------------------------------------------------
class AgentState(TypedDict):
    """Enhanced state with context tracking from your project."""
    messages: Annotated[List, add_messages]
    previous_answers: Dict[str, Any]  # Track answers for multi-question chains
    context: Dict[str, Any]  # Rich context from pages
    start_time: float  # For time tracking


# All available tools
TOOLS = [
    run_code,
    get_rendered_html,
    download_file,
    post_request,
    add_dependencies,
    transcribe_audio,
    extract_context,
    analyze_image,
    create_visualization,
    create_chart_from_data
]



# -------------------------------------------------
# SIMPLE LLM CONFIGURATION
# -------------------------------------------------
from api_key_rotator import get_api_key_rotator

# Simple configuration: Use Gemini or OpenAI
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() in ("true", "1", "yes")

# OpenAI model configuration (with backward compatibility)
# Check for old OPENAI_MODEL first for backward compatibility
OPENAI_MODEL = os.getenv("OPENAI_MODEL")  # Old variable
FALLBACK_OPENAI_MODEL = os.getenv("FALLBACK_OPENAI_MODEL", OPENAI_MODEL or "gpt-4o-mini")
PRIMARY_OPENAI_MODEL = os.getenv("PRIMARY_OPENAI_MODEL", FALLBACK_OPENAI_MODEL)

# Initialize API key rotator (for Gemini)
try:
    api_rotator = get_api_key_rotator()
    print(f"[AGENT] API Key Rotation: {api_rotator.key_count} key(s) available")
except Exception as e:
    print(f"[AGENT] Warning: API key rotation failed: {e}")
    print(f"[AGENT] Falling back to single API key")
    api_rotator = None

rate_limiter = InMemoryRateLimiter(
    requests_per_second=9/60,  # 9 requests per minute
    check_every_n_seconds=1,
    max_bucket_size=9
)

def create_gemini_llm():
    """Create Gemini LLM with rotation."""
    if api_rotator:
        api_key = api_rotator.get_next_key()
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
    
    return init_chat_model(
        model_provider="google_genai",
        model="gemini-2.5-flash",
        api_key=api_key,
        rate_limiter=rate_limiter
    ).bind_tools(TOOLS)

def create_openai_llm(use_fallback=False):
    """Create OpenAI LLM."""
    model = FALLBACK_OPENAI_MODEL if use_fallback else PRIMARY_OPENAI_MODEL
    return init_chat_model(
        model_provider="openai",
        model=model,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    ).bind_tools(TOOLS)

if USE_GEMINI:
    print(f"[AGENT] Primary LLM: Gemini (gemini-2.5-flash)")
    print(f"[AGENT] Fallback LLM: OpenAI ({FALLBACK_OPENAI_MODEL})")
    if api_rotator:
        print(f"[AGENT] Gemini keys available: {api_rotator.key_count}")
else:
    print(f"[AGENT] Primary LLM: OpenAI ({PRIMARY_OPENAI_MODEL})")
    if PRIMARY_OPENAI_MODEL == FALLBACK_OPENAI_MODEL:
        print(f"[AGENT] Fallback LLM: OpenAI (same model)")
    else:
        print(f"[AGENT] Fallback LLM: OpenAI ({FALLBACK_OPENAI_MODEL})")





# -------------------------------------------------
# ENHANCED SYSTEM PROMPT
# -------------------------------------------------
SYSTEM_PROMPT = f"""You are an autonomous quiz-solving agent with advanced capabilities for data science tasks.

Your job is to:
1. Load the quiz page from the given URL using get_rendered_html
2. Extract ALL instructions, required parameters, submission rules, and the submit endpoint
3. Use extract_context to find API URLs, JavaScript code, and forms
4. Solve the task exactly as required using available tools
5. Submit the answer ONLY to the endpoint specified on the current page
6. Read the server response and:
   - If it contains a new quiz URL → fetch it immediately and continue
   - If no new URL is present → return "END"

AVAILABLE TOOLS:

📥 DATA SOURCING:
- get_rendered_html(url): Fetch and render HTML pages with JavaScript execution
- extract_context(html, base_url): Extract submit URLs, APIs, JavaScript, forms from HTML
- download_file(url, filename): Download files (PDFs, CSVs, images, audio, etc.)

🔍 DATA PROCESSING:
- run_code(code): Execute Python code safely (90s timeout)
  * Use for data processing, ML analysis, visualization
  * Returns answer in stdout (use this for submission)
  * Use for data cleansing, transformation, filtering, sorting, aggregating
  * Available libraries: pandas, numpy, scipy, scikit-learn, httpx, pdfplumber, beautifulsoup4
  * For ML: sklearn models, statistical analysis, geo-spatial analysis
- transcribe_audio(audio_url): Transcribe audio with multi-fallback (SpeechRecognition → Gemini → Whisper)
- analyze_image(image_url, question): Analyze images using Gemini Vision (OCR, chart reading, etc.)

📊 DATA VISUALIZATION:
- create_visualization(data_description, chart_type, title): Generate charts as base64 images
  * Supports: bar, line, scatter, pie, histogram, heatmap, box plots
  * Uses matplotlib/seaborn
  * Returns base64 PNG string - SUBMIT IMMEDIATELY using post_request
- create_chart_from_data(data_code, chart_config): Custom chart with full control
  * Write custom Python for data prep and visualization
  * Returns base64 PNG string - SUBMIT IMMEDIATELY using post_request

🚀 UTILITIES:
- add_dependencies(packages): Install Python packages dynamically
- post_request(url, payload, headers): Submit answers with retry logic and time tracking

STRICT RULES — FOLLOW EXACTLY:

VISUALIZATION RULES (CRITICAL FOR SPEED):
- When create_visualization or create_chart_from_data returns a base64 string:
  * DO NOT analyze or think about the result
  * IMMEDIATELY call post_request to submit it
  * The base64 string IS the answer - submit it directly
  * Example: post_request(submit_url, payload with answer field set to base64_result)

GENERAL RULES:
- NEVER stop early. Continue solving tasks until no new URL is provided
- NEVER hallucinate URLs, endpoints, fields, values, or JSON structure
- NEVER shorten or modify URLs. Always submit the full URL
- ALWAYS inspect the server response before deciding what to do next
- ALWAYS use extract_context after loading a page to find submit URLs and APIs
- For code generation: assign final answer to variable named 'answer'
- For code: DO NOT include submission code (httpx.post) - use post_request tool instead

DATA SCIENCE TASK TYPES:

1. SCRAPING (with JavaScript):
   - Use get_rendered_html for dynamic pages
   - Use extract_context to find APIs and data sources
   - Parse HTML with BeautifulSoup in run_code

2. API SOURCING:
   - Use extract_context to discover API endpoints
   - Sample APIs to discover field names
   - Use run_code with httpx for API calls with custom headers

3. DATA CLEANSING:
   - Use run_code with pandas for cleaning text, CSV, JSON data
   - Use pdfplumber for PDF text extraction
   - Handle missing values, duplicates, formatting

4. DATA PROCESSING:
   - Audio: Use transcribe_audio (multi-fallback)
   - Images: Use analyze_image for OCR, chart reading, visual analysis
   - Text: Use run_code for NLP, regex, parsing

5. DATA ANALYSIS:
   - Filtering, sorting, aggregating: pandas in run_code
   - Statistical analysis: numpy, scipy in run_code
   - ML models: scikit-learn in run_code
   - Geo-spatial: geopandas (install with add_dependencies)
   - Network analysis: networkx (install with add_dependencies)

6. DATA VISUALIZATION:
   - Simple charts: Use create_visualization
   - Custom charts: Use create_chart_from_data
   - Interactive: Generate matplotlib/seaborn and return as base64
   - Always return base64-encoded PNG for submission

TIME LIMIT RULES:
- Each task has a hard 3-minute limit
- The server response includes a "delay" field indicating elapsed time
- If your answer is wrong and delay < 180s, you can retry
- If delay >= 180s, move to next question (if URL provided)

CONTEXT AWARENESS:
- Use extract_context to discover API endpoints and sample their data
- For audio tasks, use transcribe_audio (it has fallback mechanisms)
- For image tasks, use analyze_image (Gemini Vision + OpenAI fallback)
- For PDFs, download first then process with run_code
- Track previous answers in state for multi-question chains

CODE GENERATION BEST PRACTICES:
- NEVER hardcode data - always fetch from APIs/files
- ALWAYS inspect API responses to discover field names
- Extract and analyze JavaScript code instead of guessing logic
- Use context variables (previous_answers) when available
- Assign ONLY the final answer value to 'answer' variable (not submission payload)
- For visualizations, return base64-encoded PNG string

ML/STATISTICAL ANALYSIS EXAMPLES:
- Linear regression: Use sklearn.linear_model.LinearRegression
- Classification: Use sklearn models (LogisticRegression, RandomForest, etc.)
- Clustering: Use sklearn.cluster (KMeans, DBSCAN, etc.)
- Statistical tests: Use scipy.stats
- Time series: Use pandas datetime functions
- Correlation: Use pandas.DataFrame.corr()

VISUALIZATION EXAMPLES:
- Bar chart: create_visualization("data from API /sales", "bar", "Sales by Month")
- Custom: create_chart_from_data("df = pd.read_json(...)", "plt.bar(df.x, df.y)")
- Heatmap: create_visualization("correlation matrix of features", "heatmap")

STOPPING CONDITION:
- Only return "END" when a server response explicitly contains NO new URL
- DO NOT return END under any other condition

ADDITIONAL INFORMATION YOU MUST INCLUDE WHEN REQUIRED:
- Email: {EMAIL}
- Secret: {SECRET}

YOUR JOB:
- Follow pages exactly
- Extract data reliably using tools
- Apply ML/statistical analysis when needed
- Generate visualizations as base64 images
- Never guess
- Submit correct answers
- Continue until no new URL
- Then respond with: END
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="messages")
])


# -------------------------------------------------
# AGENT NODE WITH SIMPLE CONFIGURATION
# -------------------------------------------------
def agent_node(state: AgentState):
    """Agent decision-making node with simple USE_GEMINI configuration."""
    print(f"\n[AGENT] 🤖 LLM thinking...")
    
    if USE_GEMINI:
        # Use Gemini with OpenAI fallback
        # Check if all Gemini keys exhausted
        if api_rotator and api_rotator.are_all_keys_exhausted():
            print(f"[AGENT] 🔄 All Gemini keys exhausted, using OpenAI")
            return use_openai(state)
        
        # Try Gemini
        try:
            llm = create_gemini_llm()
            llm_with_prompt = prompt | llm
            result = llm_with_prompt.invoke({"messages": state["messages"]})
            log_llm_decision(result, "Gemini")
            return {"messages": state["messages"] + [result]}
            
        except Exception as e:
            error_msg = str(e)
            print(f"[AGENT] ❌ Gemini failed: {error_msg[:200]}")
            
            # Check if it's a quota error
            is_quota_error = any(keyword in error_msg.lower() 
                               for keyword in ["quota", "429", "resource_exhausted", "rate limit"])
            
            if is_quota_error and api_rotator:
                print(f"[AGENT] 🔄 Quota exceeded on current Gemini key")
                current_key_index = (api_rotator._current_index - 1) % api_rotator.key_count
                api_rotator.mark_key_exhausted(current_key_index)
                
                if api_rotator.are_all_keys_exhausted():
                    print(f"[AGENT] 🔄 All Gemini keys exhausted, switching to OpenAI")
                else:
                    print(f"[AGENT] 🔄 Trying next Gemini key...")
                    return agent_node(state)
            
            # Fallback to OpenAI
            print(f"[AGENT] 🔄 Switching to OpenAI fallback")
            return use_openai(state, use_fallback=True)
    
    else:
        # Use OpenAI only
        return use_openai(state)

def use_openai(state: AgentState, use_fallback=False):
    """Use OpenAI LLM."""
    try:
        llm = create_openai_llm(use_fallback=use_fallback)
        llm_with_prompt = prompt | llm
        result = llm_with_prompt.invoke({"messages": state["messages"]})
        model_name = FALLBACK_OPENAI_MODEL if use_fallback else PRIMARY_OPENAI_MODEL
        log_llm_decision(result, f"OpenAI ({model_name})")
        return {"messages": state["messages"] + [result]}
    except Exception as e:
        print(f"[AGENT] ❌ OpenAI failed: {str(e)[:200]}")
        raise Exception("LLM failed")

def log_llm_decision(result, llm_type="LLM"):
    """Log what the LLM decided to do."""
    if hasattr(result, "tool_calls") and result.tool_calls:
        print(f"[AGENT] 🔧 {llm_type} decided to call {len(result.tool_calls)} tool(s):")
        for i, tool_call in enumerate(result.tool_calls, 1):
            tool_name = tool_call.get("name", "unknown")
            print(f"[AGENT]   {i}. {tool_name}")
    elif hasattr(result, "content"):
        content = result.content
        if isinstance(content, str):
            preview = content[:100] + "..." if len(content) > 100 else content
            print(f"[AGENT] 💬 {llm_type} response: {preview}")



# -------------------------------------------------
# GRAPH ROUTING
# -------------------------------------------------
def route(state):
    """Route based on last message."""
    last = state["messages"][-1]
    
    # Support both objects and dicts
    tool_calls = None
    if hasattr(last, "tool_calls"):
        tool_calls = getattr(last, "tool_calls", None)
    elif isinstance(last, dict):
        tool_calls = last.get("tool_calls")

    if tool_calls:
        return "tools"
    
    # Get content robustly
    content = None
    if hasattr(last, "content"):
        content = getattr(last, "content", None)
    elif isinstance(last, dict):
        content = last.get("content")

    if isinstance(content, str) and content.strip() == "END":
        return END
    if isinstance(content, list) and content[0].get("text", "").strip() == "END":
        return END
    
    return "agent"


# Build graph
graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(TOOLS))

graph.add_edge(START, "agent")
graph.add_edge("tools", "agent")
graph.add_conditional_edges(
    "agent",
    route
)

app = graph.compile()


# -------------------------------------------------
# RUN AGENT
# -------------------------------------------------
def run_agent(url: str) -> str:
    """Run the agent on a quiz URL."""
    print(f"\n{'='*60}")
    print(f"[AGENT] Starting quiz chain")
    print(f"[AGENT] URL: {url}")
    print(f"{'='*60}\n")
    
    # Reset submission tracking
    from hybrid_tools.send_request import reset_submission_tracking
    reset_submission_tracking()
    
    # Start periodic log uploads (every 5 minutes)
    start_periodic_uploads()
    
    # Initialize state
    start_time = time.time()
    initial_state = {
        "messages": [{"role": "user", "content": url}],
        "previous_answers": {},
        "context": {},
        "start_time": start_time
    }
    
    try:
        app.invoke(
            initial_state,
            config={"recursion_limit": RECURSION_LIMIT}
        )
        
        total_time = time.time() - start_time
        print(f"\n[AGENT] ✓ Tasks completed successfully")
        print(f"[AGENT] Total time: {total_time:.1f}s")
        
        # Stop periodic uploads
        stop_periodic_uploads()
        
        # Upload full log file to GitHub Gist if configured
        try:
            from remote_logger import upload_to_github_gist
            import glob
            import os
            
            # Find the most recent log file
            log_files = glob.glob("hybrid_logs_*.txt")
            if log_files:
                latest_log = max(log_files, key=os.path.getctime)
                with open(latest_log, 'r') as f:
                    log_content = f.read()
                
                upload_to_github_gist(
                    content=log_content,
                    description=f"Quiz Solver Success - {url} - {total_time:.1f}s"
                )
        except Exception as log_error:
            # Don't fail if logging fails
            pass
        
        return "success"
    except Exception as e:
        total_time = time.time() - start_time
        print(f"\n[AGENT] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Stop periodic uploads
        stop_periodic_uploads()
        
        # Upload full log file to GitHub Gist if configured
        try:
            from remote_logger import upload_to_github_gist
            import glob
            import os
            
            # Find the most recent log file
            log_files = glob.glob("hybrid_logs_*.txt")
            if log_files:
                latest_log = max(log_files, key=os.path.getctime)
                with open(latest_log, 'r') as f:
                    log_content = f.read()
                
                upload_to_github_gist(
                    content=log_content,
                    description=f"Quiz Solver Error - {url} - {str(e)[:50]}"
                )
        except Exception as log_error:
            pass
        
        return f"error: {e}"
