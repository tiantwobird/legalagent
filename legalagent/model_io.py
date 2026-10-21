"""One place that decides whether a model may be downloaded.

Every entry point used to hardcode ``local_files_only=True``, which made a fresh
clone fail on its first run: nothing was in the Hugging Face cache, and the error
looked like a broken model path rather than "you are offline by default".

Now each script exposes ``--download`` (and the env var
``LEGALAGENT_ALLOW_DOWNLOAD=1`` does the same for every process), and the
decision is made here.

Transformers / torch imports stay inside the functions so that importing this
module is free — the unit tests and CI never pull the training stack.
"""

from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on"}

_MISSING_HINT = (
    "{model_id} 不在本地缓存，且当前处于离线模式。\n"
    "首次运行请加 --download（或设置 LEGALAGENT_ALLOW_DOWNLOAD=1）让它下载，"
    "或者先把模型拉到本地。"
)


def allow_download(explicit: bool = False) -> bool:
    """True when the caller passed --download or the env var is set."""
    if explicit:
        return True
    return os.environ.get("LEGALAGENT_ALLOW_DOWNLOAD", "").strip().lower() in _TRUE


def load_tokenizer(model_id: str, download: bool = False):
    from transformers import AutoTokenizer

    try:
        return AutoTokenizer.from_pretrained(
            model_id, local_files_only=not allow_download(download)
        )
    except OSError as exc:
        raise SystemExit(_MISSING_HINT.format(model_id=model_id)) from exc


def load_model(model_id: str, download: bool = False, dtype=None):
    """Load a causal LM; `dtype` is passed through (bf16, "auto", ...)."""
    from transformers import AutoModelForCausalLM

    kwargs = {"local_files_only": not allow_download(download)}
    if dtype is not None:
        kwargs["dtype"] = dtype
    try:
        return AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except OSError as exc:
        raise SystemExit(_MISSING_HINT.format(model_id=model_id)) from exc


def resolve_device(prefer: str = "cuda") -> str:
    """`prefer` if it is usable, otherwise cpu."""
    import torch

    if prefer == "cuda" and torch.cuda.is_available():
        return "cuda"
    return "cpu"
