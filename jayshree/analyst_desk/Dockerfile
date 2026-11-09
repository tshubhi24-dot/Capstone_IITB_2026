# One image for the app and the four MCP servers; compose.yaml picks the
# command for each service. (The python-sandbox *code runner* image is
# separate: docker/sandbox/Dockerfile.)
#
# The team image is built by CI from main and published to
# ghcr.io/tshubhi24-dot/analyst-desk (.github/workflows/docker-image.yml).
# Build locally: docker compose build      (or: docker build -t analystdesk .)
#
# Everything that decides behaviour is pinned, so every build is the same:
# the base image, every Python package (requirements.lock), torch, and the
# embedding and reranker model snapshots.

FROM python:3.12.16-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

WORKDIR /app

# CPU-only PyTorch first: the default Linux wheel bundles CUDA (~3 GB more)
ARG TORCH_VERSION=2.15.0+cpu
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}"

# Exact versions (see the header of requirements.lock for how to update them)
ARG REQUIREMENTS=requirements.lock
COPY requirements.txt requirements.lock ./
RUN pip install -r "${REQUIREMENTS}" && pip check

# Bake the embedding and reranker models into the image, at fixed snapshots, so
# containers run offline and every teammate uses identical model files.
# A download pinned to a commit does not set the cache's "main" ref, and the app
# loads the models by name (= main) offline, so main is pointed at the pinned
# snapshot; the final line fails the build if loading by name does not work.
ARG EMBEDDER_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41
ARG RERANKER_REVISION=233902d25c440f23af6f7d6e94d2946bac0bee0a
# Only the files sentence-transformers loads: the repos also hold ONNX, OpenVINO,
# TensorFlow, Flax and Rust copies of the weights (~1.5 GB the app never reads)
RUN python -c "from huggingface_hub import snapshot_download; \
files = ['*.json', '*.txt', 'model.safetensors', '1_Pooling/*']; \
snapshot_download('sentence-transformers/all-MiniLM-L6-v2', revision='${EMBEDDER_REVISION}', allow_patterns=files); \
snapshot_download('cross-encoder/ms-marco-MiniLM-L-6-v2', revision='${RERANKER_REVISION}', allow_patterns=files)" \
    && mkdir -p /opt/hf/hub/models--sentence-transformers--all-MiniLM-L6-v2/refs \
                /opt/hf/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2/refs \
    && printf '%s' "${EMBEDDER_REVISION}" > /opt/hf/hub/models--sentence-transformers--all-MiniLM-L6-v2/refs/main \
    && printf '%s' "${RERANKER_REVISION}" > /opt/hf/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2/refs/main \
    && chmod -R a+rX /opt/hf \
    && HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python -c "from sentence_transformers import \
SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

# The non-root user and its writable spots for the named volumes (index, runs,
# memory, portal, approval). Docker copies this content and ownership into a new volume, so the
# user can write there and a new index volume starts with the baked index.
# Created before the index is built, so the index is written once, as this user
# (a chown afterwards would copy it into another layer).
RUN useradd --create-home --uid 1000 desk \
    && mkdir -p data/index data/runs data/memory data/portal data/approval && chown -R desk data

COPY analystdesk/ analystdesk/
COPY config/ config/
COPY scripts/ scripts/
COPY experiments/ experiments/
COPY app.py agent_ui.py eval_ui.py ./

# Bake the search index (Chroma) into the image, built from the committed
# passages, so a teammate's first start skips the ~25-minute embedding. At run
# time compose still mounts data/ from the repo: the index is named after a
# fingerprint of the passages, so if a checkout's passages differ from the
# image's, the index service simply builds a matching one. BAKE_INDEX=0 skips
# it (CI does that for pull-request test builds).
USER desk
ARG BAKE_INDEX=1
COPY --chown=desk data/passages/ data/passages/
RUN if [ "$BAKE_INDEX" = "1" ]; then \
      python -c "from analystdesk.retrieve import get_retriever; get_retriever()"; \
    fi

EXPOSE 7861
CMD ["python", "app.py"]
