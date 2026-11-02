# One image for the app and the four MCP servers; compose.yaml picks the
# command for each service. (The python-sandbox *code runner* image is
# separate: docker/sandbox/Dockerfile.)
#
# Build: docker compose build      (or: docker build -t analystdesk .)

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

WORKDIR /app

# CPU-only PyTorch first: the default Linux wheel bundles CUDA (~3 GB more)
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding and reranker models into the image, so containers run
# offline and every teammate uses identical model files
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')" \
    && chmod -R a+rX /opt/hf
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY analystdesk/ analystdesk/
COPY config/ config/
COPY scripts/ scripts/
COPY app.py agent_ui.py eval_ui.py ./

# Committed data (passages, XBRL JSON) is mounted from the repo at runtime,
# so the image never goes stale when data is refreshed.
# Writable spots for the named volumes (index, portal); Docker copies this
# ownership into a new volume, so the non-root user can write there
RUN useradd --create-home --uid 1000 desk \
    && mkdir -p data/index data/portal data/approval && chown -R desk data
USER desk

EXPOSE 7861
CMD ["python", "app.py"]
