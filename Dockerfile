FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app
COPY pyproject.toml README.md ./
COPY harness ./harness
COPY mock ./mock
COPY skills ./skills
RUN pip install --no-cache-dir . && python -m playwright install --with-deps chromium \
    && useradd --create-home --uid 1000 agent \
    && mkdir -p /app/data && chown agent:agent /app/data \
    && chmod -R a+rX /ms-playwright
USER agent
ENV HOST=0.0.0.0 PORT=8787 DATA_DIR=/app/data SKILLS_DIR=/app/skills INTERNAL_URL=http://127.0.0.1:8787
VOLUME ["/app/data"]
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/health',timeout=3)"
CMD ["python", "-m", "harness.web"]
