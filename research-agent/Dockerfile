# Deep Research Agent - AgentCore Runtime
# LangGraph-based dimensional research workflow
FROM public.ecr.aws/docker/library/python:3.13-slim

WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_CONTAINER=1 \
    AWS_DEFAULT_REGION=us-west-2 \
    HOME=/tmp

# Install system dependencies including LibreOffice for PDF conversion
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libreoffice-writer \
    libreoffice-core \
    libreoffice-common \
    fonts-liberation \
    xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/.config/libreoffice \
    && chmod -R 777 /tmp/.config

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir bedrock-agentcore

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

# Expose ports
EXPOSE 8080
EXPOSE 8000

# Copy application code (after user switch for proper permissions)
COPY --chown=bedrock_agentcore:bedrock_agentcore src/ ./src/

# Copy shared configuration (model mappings, copied into build context by buildspec)
COPY --chown=bedrock_agentcore:bedrock_agentcore shared/ ./shared/

# Set Python path to include shared directory
ENV PYTHONPATH=/app:/app/shared

# Run the research agent
CMD ["python", "-m", "src.agent"]
