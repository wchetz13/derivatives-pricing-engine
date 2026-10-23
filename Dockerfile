# syntax=docker/dockerfile:1

FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir build && python -m build --wheel --outdir /dist

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 10001 app
COPY --from=build /dist/*.whl /tmp/
RUN WHEEL=$(ls /tmp/*.whl) && pip install --no-cache-dir "${WHEEL}[api]" && rm /tmp/*.whl
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "pricing_engine.api:app", "--host", "0.0.0.0", "--port", "8000"]
