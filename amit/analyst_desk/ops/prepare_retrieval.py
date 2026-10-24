"""Prepare frozen local retrieval artifacts using public cached model files.

This command never contacts a model provider or the Hub. Obtain the pinned
public snapshots separately if they are not already in the specified cache.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.data import Corpus
from desk.retrieval import (HybridRetriever, LocalModels, RetrievalError, document_text,
                            load_config, verify_model_files, write_index)


def prepare(corpus_path, output, model_cache, *, config_path=None):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    config = load_config(config_path)
    corpus = Corpus(corpus_path)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        # Existing complete bundles are reusable; do not mutate files in use.
        retriever = HybridRetriever(corpus, artifacts=output, config=config)
        retriever.load_index()
        for role in ("encoder", "reranker"):
            verify_model_files(output / "models" / role, config[role])
        return {"status": "reused", "manifest": retriever.manifest}
    temporary = Path(tempfile.mkdtemp(prefix=output.name + ".prepare-", dir=output.parent))
    try:
        for role in ("encoder", "reranker"):
            spec = config[role]
            snapshot = Path(model_cache) / ("models--" + spec["id"].replace("/", "--")) / "snapshots" / spec["revision"]
            for name, expected in spec["files"].items():
                source = snapshot / name
                if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                    raise RetrievalError("The required public pinned model snapshot is not present in the cache.")
                destination = temporary / "models" / role / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            verify_model_files(temporary / "models" / role, spec)
        models = LocalModels(temporary / "models", config)
        rows = sorted(corpus._passages.values(), key=lambda row: row["id"])
        texts = [document_text(row, config["table_aware"]) for row in rows]
        vectors = models.encode(texts)
        manifest = write_index(temporary, corpus.fingerprint, rows, vectors, config)
        receipt = {"status": "prepared", "manifest": manifest,
                   "packages": {name: version(name) for name in ("sentence-transformers", "transformers", "torch", "numpy")},
                   "paid_model_calls": 0, "network_requests": 0}
        (temporary / "preparation_receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        temporary.replace(output)
        return receipt
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-cache", type=Path, default=Path.home() / ".cache/huggingface/hub")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    result = prepare(args.corpus, args.output, args.model_cache, config_path=args.config)
    manifest = result["manifest"]
    print(json.dumps({"status": result["status"], "passages": manifest["passage_count"],
                      "dimension": manifest["dimension"], "index_fingerprint": manifest["index_fingerprint"],
                      "corpus_fingerprint": manifest["corpus_fingerprint"], "paid_model_calls": 0,
                      "network_requests": 0}))


if __name__ == "__main__":
    main()
