FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home mcp \
    && git config --system --add safe.directory /app \
    && git config --system --add safe.directory /app/serbia/national/acts
WORKDIR /opt/runtime
COPY requirements-serbia.txt .
RUN pip install --no-cache-dir -r requirements-serbia.txt
WORKDIR /app
USER mcp
ENV GLOBAL_LAW_JURISDICTIONS=serbia GLOBAL_LAW_HOSTED=1 SERBIA_LAW_MCP=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
# /app is the pinned host checkout; its cache is mounted separately writable.
CMD ["python", "-m", "uvicorn", "serbia_http:app", "--app-dir", "tools", "--host", "0.0.0.0", "--port", "8080"]
