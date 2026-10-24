FROM python:3.12.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 RUNTIME_DIR=/runtime CORPUS_PATH=/sources/corpus.json
WORKDIR /app
RUN groupadd --gid 10001 analyst && useradd --uid 10001 --gid analyst --no-create-home analyst \
    && mkdir -p /runtime /queue /sources /secrets/app /secrets/filings-kb /secrets/edgar /secrets/python-sandbox /secrets/research-portal /secrets/metrics /secrets/grafana /secrets/chroma /secrets/queue /secrets/model-gateway \
    && chown -R analyst:analyst /runtime /queue /sources /secrets
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY desk ./desk
COPY ops/bootstrap.py ./ops/bootstrap.py
COPY ops/verify_catalogue_tools.py ./ops/verify_catalogue_tools.py
COPY web ./web
USER 10001:10001
ENTRYPOINT ["python", "ops/bootstrap.py", "exec"]
CMD ["python", "-m", "uvicorn", "desk.api:app", "--host", "0.0.0.0", "--port", "8000"]
