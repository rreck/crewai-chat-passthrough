# Copyright (c) RRECKTEK LLC
# CrewAI Chat Passthrough Agent - Pure Claude Integration
# Version: 1.0.0

FROM rockylinux:9

ENV LANG=en_US.UTF-8

# Install Python and dependencies
RUN dnf install -y --allowerasing python3 python3-pip curl && \
    dnf clean all

# Install Python packages
RUN pip3 install --no-cache-dir \
    flask \
    prometheus-client \
    requests

# Create application directory
WORKDIR /opt/app

# Copy application files
COPY app/ /opt/app/

# Create necessary directories
RUN mkdir -p /work/input /work/output /work/output/logs /work/data /work/kb/short /work/kb/long /var/run

# Create non-root user
RUN useradd -m -u 1000 crewai && \
    chown -R crewai:crewai /opt/app /work /var/run

# Switch to non-root user
USER crewai

# Expose ports
EXPOSE 8080 9090

# Environment variables
ENV INPUT_DIR=/work/input \
    OUTPUT_DIR=/work/output \
    DATA_DIR=/work/data \
    PIDFILE=/work/crewai-chat-passthrough.pid \
    METRICS_PORT=9090 \
    API_PORT=8080 \
    C2_REGISTRY_URL=http://crewai-c2-dc1-prod-001-v1-0-0:8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the agent
CMD ["python3", "/opt/app/main.py"]
