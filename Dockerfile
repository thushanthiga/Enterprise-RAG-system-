FROM nvidia/cuda:12.1.0-base-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    git \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Setup workspace
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Ensure index directory exists
RUN mkdir -p /app/index /mnt/company-docs

# Make scripts executable
RUN chmod +x /app/run.sh

# Expose ports: Streamlit(8501), FastAPI(8000), Ollama(11434)
EXPOSE 8501 8000 11434

# Entrypoint
CMD ["/bin/bash", "/app/run.sh"]
