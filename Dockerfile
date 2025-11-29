FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy ALL files first (needed for uv to read pyproject.toml properly)
COPY . .

# Install Python dependencies with uv
RUN uv pip install --system --no-cache .

# Install Playwright and its dependencies
RUN playwright install --with-deps chromium

# Create directory for file operations
RUN mkdir -p /app/hybrid_llm_files

# Expose port (HF Spaces uses 7860)
EXPOSE 7860

# Run the application
CMD ["uvicorn", "hybrid_main:app", "--host", "0.0.0.0", "--port", "7860"]
