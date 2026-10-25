"""Concurrent searches must not share a mutating tokenizer without its lock."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import threading

import numpy as np
import pytest

from desk.retrieval import LocalModels


class TokenizerUse:
    """Deterministically hold one tokenizer borrow while a second request starts."""
    def __init__(self, hold_phase=None):
        self.hold_phase = hold_phase
        self.fail_phase = None
        self.local = threading.local()
        self.borrow = threading.Lock()
        self.entered = threading.Event()
        self.contender_progress = threading.Event()
        self.release = threading.Event()

    @contextmanager
    def phase(self, name):
        if not self.borrow.acquire(blocking=False):
            self.contender_progress.set()
            raise RuntimeError("shared tokenizer is already borrowed")
        try:
            if getattr(self.local, "role", None) == "first" and name == self.hold_phase:
                self.entered.set()
                if not self.release.wait(5):
                    raise AssertionError("test did not release the held tokenizer")
            if name == self.fail_phase:
                self.fail_phase = None
                raise ValueError("deliberate tokenizer/model failure")
            yield
        finally:
            self.borrow.release()


class ObservedLock:
    def __init__(self, use):
        self.use = use
        self.lock = threading.Lock()

    def __enter__(self):
        if getattr(self.use.local, "role", None) == "second":
            self.use.contender_progress.set()
        self.lock.acquire()

    def __exit__(self, *exc):
        self.lock.release()


class StatefulTokenizer:
    def __init__(self, use):
        self.use = use

    def __call__(self, text, **kwargs):
        phase = "window" if kwargs.get("return_offsets_mapping") else "query"
        with self.use.phase(phase):
            if phase == "window":
                return {"offset_mapping": [(index, index + 1) for index in range(len(text))]}
            return {"input_ids": [ord(char) for char in text[:kwargs["max_length"]]]}

    def decode(self, tokens, **kwargs):
        with self.use.phase("decode"):
            return "".join(map(chr, tokens))


class StubEncoder:
    def __init__(self, use):
        self.use = use
        self.tokenizer = StatefulTokenizer(use)

    def encode(self, texts, **kwargs):
        with self.use.phase("inference"):
            vectors = np.asarray([[len(text), 1., 0., 0.] for text in texts], dtype=np.float32)
            return (vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
                    if texts else np.empty((0, 4), dtype=np.float32))


class StubReranker:
    def __init__(self, use):
        self.use = use
        self.tokenizer = StatefulTokenizer(use)

    def predict(self, pairs, **kwargs):
        with self.use.phase("inference"):
            return np.asarray([text.count("target") for _, text in pairs], dtype=np.float32)


def local_models(use):
    # Exercise production preprocessing/inference methods without downloading models.
    models = LocalModels.__new__(LocalModels)
    models.config = {"dimension": 4, "encoder": {"max_length": 64},
                     "reranker": {"max_length": 64}}
    models.encoder = StubEncoder(use)
    models.reranker = StubReranker(use)
    models.lock = ObservedLock(use)
    return models


def invoke(models, operation, label):
    documents = [label + " target " * 16, label + " other " * 12]
    return (models.encode(documents) if operation == "encode"
            else models.score("risk query", documents))


PHASES = [("encode", "window"), ("encode", "inference"),
          ("score", "query"), ("score", "decode"),
          ("score", "window"), ("score", "inference")]


@pytest.mark.parametrize("operation,phase", PHASES)
def test_parallel_requests_lock_tokenizer_preprocessing_and_inference(operation, phase):
    use = TokenizerUse(phase)
    models = local_models(use)

    def request(role, label):
        use.local.role = role
        return invoke(models, operation, label)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(request, "first", "ABT")
        try:
            assert use.entered.wait(5), "first request never reached the selected phase"
            second = pool.submit(request, "second", "AMGN")
            # The contender either reaches the model lock (correct) or collides
            # with the held tokenizer (the original defect). No scheduling sleep.
            assert use.contender_progress.wait(5), "second request never entered retrieval"
        finally:
            use.release.set()
        results = [first.result(timeout=5), second.result(timeout=5)]

    use.hold_phase = None
    expected = [invoke(models, operation, label) for label in ("ABT", "AMGN")]
    for actual, serial in zip(results, expected):
        np.testing.assert_array_equal(actual, serial)
        assert np.isfinite(actual).all()
        if operation == "encode":
            np.testing.assert_allclose(np.linalg.norm(actual, axis=1), 1.)


@pytest.mark.parametrize("operation,phase", PHASES)
def test_tokenizer_or_inference_failure_releases_the_shared_model_lock(operation, phase):
    use = TokenizerUse()
    use.fail_phase = phase
    models = local_models(use)
    with pytest.raises(ValueError, match="deliberate tokenizer/model failure"):
        invoke(models, operation, "ABT")
    assert models.lock.lock.acquire(blocking=False), "failure leaked the model lock"
    models.lock.lock.release()
    assert np.isfinite(invoke(models, operation, "AMGN")).all()


def test_empty_model_inputs_keep_their_existing_result_shapes():
    models = local_models(TokenizerUse())
    assert models.encode([]).shape == (0, 4)
    assert models.score("risk query", []).shape == (0,)
