FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* && useradd --create-home mcp
WORKDIR /app
RUN chown mcp:mcp /app
COPY requirements-serbia.txt .
RUN pip install --no-cache-dir -r requirements-serbia.txt
COPY --chown=mcp:mcp . .
USER mcp
ENV GLOBAL_LAW_JURISDICTIONS=serbia GLOBAL_LAW_HOSTED=1 SERBIA_LAW_MCP=1 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "serbia_http:app", "--app-dir", "tools", "--host", "0.0.0.0", "--port", "8080"]
