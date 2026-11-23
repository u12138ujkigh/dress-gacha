# -*- coding: utf-8 -*-
"""Runtime model discovery for the dress-gacha engine.

Chinese folder names come back from ComfyUI as mojibake in a terminal, so nothing
here is hard-coded as a literal path: every model and LoRA is matched by an ASCII
substring that survives encoding damage, then the exact string is kept verbatim
for the API call.
"""
from __future__ import annotations

import functools
import json
import os
import threading
import urllib.request

BASE = os.environ.get("COMFYUI_BASE", "http://127.0.0.1:8188")

# Single source of truth for generated-image placement. The user's ComfyUI
# Desktop keeps its output at E:\Comfy-Desktop\ComfyUI-Shared\output. This app's
# images live in the 1图片/正反面和大头 subfolder of that root. ComfyUI's
# SaveImage node writes there directly, so the server never makes a second copy.
COMFY_OUTPUT_ROOT = os.environ.get(
    "COMFYUI_OUTPUT_ROOT", r"E:\Comfy-Desktop\ComfyUI-Shared\output")
WEBUI_OUT = os.environ.get(
    "DRESS_GACHA_OUT",
    os.path.join(COMFY_OUTPUT_ROOT, "1图片", "正反面和大头"))


def free_vram(timeout: float = 30) -> bool:
    """Ask ComfyUI to unload every cached model before a job starts.

    Best effort only: a busy queue is left untouched so a user-run job in the
    ComfyUI UI is never yanked out from under. Called at the top of every render
    and every `comfy:` write so a previous model's VRAM/RAM cache is gone first.
    """
    try:
        with urllib.request.urlopen(BASE + "/queue", timeout=timeout) as r:
            q = json.loads(r.read().decode("utf-8"))
        if q.get("queue_running") or q.get("queue_pending"):
            return False
        body = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
        req = urllib.request.Request(BASE + "/free", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=timeout).read()
        return True
    except Exception:
        return False

# One ComfyUI, one GPU. Everything that drives ComfyUI — a `comfy:` local write
# (text generation) and any image render — must own the GPU for its whole
# submit→wait→collect lifetime, or a text model and an image model fight over
# the same VRAM and get swapped in/out mid-job. This lock is that ownership
# token. Cloud/relay writes never take it (they don't touch ComfyUI), so they
# still run in parallel with a render.
# RLock so a caller can nest serialize_gpu() inside another without deadlock.
GPU_LANE_LOCK = threading.RLock()


def serialize_gpu(fn):
    """Run `fn` while holding the ComfyUI GPU for its entire duration."""
    @functools.wraps(fn)
    def _wrapped(*args, **kwargs):
        with GPU_LANE_LOCK:
            return fn(*args, **kwargs)
    return _wrapped

# tier -> which Krea2 mix to use
TIER_UNET = {
    "normal": "moodyAmateurMixKrea2_v50ProsumerShots_int8.safetensors",
    "edgy": "moodyAmateurMixKrea2_v50ProsumerShots_int8.safetensors",
    "nude": "moodyKrea2MixUncensoredV8SEGoes_v80_int8.safetensors",
    "explicit": "moodyKrea2MixUncensoredV8SEGoes_v80_int8.safetensors",
}

CLIP_HINT = "qwen3vl_4b_fp8_scaled"
VAE_HINT = "qwen_image_vae"
LORA_4STEP_HINT = "turbo_4step_rank_64"


def _get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _list(folder: str) -> list[str]:
    try:
        d = _get(f"/models/{folder}")
    except Exception:
        return []
    return d if isinstance(d, list) else d.get("files", [])


def _pick(items: list[str], hint: str) -> str | None:
    for i in items:
        if hint.lower() in i.lower():
            return i
    return None


_CACHE: dict = {}


def discover(force: bool = False) -> dict:
    """Resolve the exact model strings this ComfyUI install will accept."""
    if _CACHE and not force:
        return _CACHE

    unets = _list("diffusion_models")
    clips = _list("text_encoders")
    vaes = _list("vae")
    loras = _list("loras")

    tier_unet: dict[str, str] = {}
    for tier, fname in TIER_UNET.items():
        hit = next((u for u in unets if u.endswith(fname)), None)
        if not hit:
            # fall back to the first kr2 mix that exists at all
            hit = next((u for u in unets if "krea2" in u.lower()), None)
        tier_unet[tier] = hit or ""

    data = {
        "unet_by_tier": tier_unet,
        "clip": _pick(clips, CLIP_HINT) or "",
        "vae": _pick(vaes, VAE_HINT) or "",
        "lora_4step": _pick(loras, LORA_4STEP_HINT) or "",
        "ok": bool(tier_unet.get("normal") and data_clip(clips)),
    }
    _CACHE.clear()
    _CACHE.update(data)
    return data


def data_clip(clips: list[str]) -> str | None:
    return _pick(clips, CLIP_HINT)


if __name__ == "__main__":
    d = discover()
    for k, v in d.items():
        print(f"{k}: {v!r}")
