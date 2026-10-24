"""Populate local Chroma explicitly from an already validated retrieval artifact.

No embeddings are generated, models downloaded, provider requests issued or
existing collections overwritten. The runtime only reads this prepared store.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desk.data import Corpus
from desk.retrieval import HybridRetriever, load_config
from desk.vector_store import populate_chroma


def prepare(corpus_path, artifacts, chroma_url, *, config_path=None, client=None):
    corpus = Corpus(corpus_path)
    retriever = HybridRetriever(corpus, artifacts=artifacts, config=load_config(config_path))
    retriever.load_index()
    return populate_chroma(retriever, chroma_url, client=client)


def wait_for_store(url, seconds):
    parsed = urlsplit(url)
    if (parsed.scheme != "http" or parsed.hostname not in {"chroma", "localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("A local Chroma URL is required")
    deadline = time.monotonic() + seconds
    while True:
        try:
            with build_opener(ProxyHandler({})).open(url.rstrip("/") + "/api/v2/heartbeat", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            if time.monotonic() >= deadline:
                raise ValueError("Local Chroma did not become ready within the bounded wait") from None
        time.sleep(.5)


def write_receipt(path, receipt):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(receipt, stream, sort_keys=True, indent=2)
        stream.write("\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--chroma-url", required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--wait-seconds", type=int, choices=range(0, 61), default=0)
    arguments = parser.parse_args()
    if arguments.output is not None:
        output = arguments.output.resolve()
        if output == arguments.corpus.resolve() or output.is_relative_to(arguments.artifacts.resolve()):
            parser.error("The receipt must be outside source documents and immutable retrieval artifacts")
    if arguments.wait_seconds:
        wait_for_store(arguments.chroma_url, arguments.wait_seconds)
    receipt = prepare(arguments.corpus, arguments.artifacts, arguments.chroma_url, config_path=arguments.config)
    if arguments.output is not None:
        write_receipt(arguments.output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
