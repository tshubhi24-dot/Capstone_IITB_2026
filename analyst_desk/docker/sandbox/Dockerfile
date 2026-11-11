# Sandbox image for the python-sandbox MCP server.
#
# Runs one untrusted calculation per container. Isolation comes from how the
# server starts it (see analystdesk/servers/sandbox.py, _docker_cmd):
#   --network none, --read-only, non-root user, --cap-drop ALL,
#   no-new-privileges, memory/CPU/process limits, time limit.
# The image itself only holds Python, pandas and the runner.
#
# Build from the analyst_desk folder:
#   docker build -t analystdesk-sandbox -f docker/sandbox/Dockerfile .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir "pandas==2.2.3" "numpy==2.1.3"

COPY analystdesk/servers/sandbox_runner.py /sandbox/runner.py

USER 65534:65534
WORKDIR /tmp

ENTRYPOINT ["python", "-I", "-B", "/sandbox/runner.py"]
