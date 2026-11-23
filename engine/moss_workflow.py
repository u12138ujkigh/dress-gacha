# -*- coding: utf-8 -*-
"""Moss workflow: load the original API-format graph from D:\\sucai\\Moss.json
and patch only the values that vary per draw.

The graph is already wired (KSampler takes steps/cfg/denoise from switch nodes,
the latent from the resolution node, and so on), so building it from scratch
breaks the links — ComfyUI answers 400. Editing a copy in place keeps every link
intact and only changes what the user asked to change.
"""
from __future__ import annotations

import copy
import json
import os

from . import config

MOSS_JSON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Moss.json"
)
MOSS_JSON_FALLBACK = r"D:\sucai\Moss.json"

_cache: dict | None = None


def _load_template() -> dict:
    global _cache
    if _cache is None:
        path = MOSS_JSON if os.path.isfile(MOSS_JSON) else MOSS_JSON_FALLBACK
        with open(path, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


# Node ids in the Moss graph that carry values a draw varies
N_TEXT = "3"
N_SEED = "4"
N_UNET = "10"
N_RESOLUTION = "5"
N_LORA = "11"
N_SAVE = "13"
N_NEG = "39:77"
N_SEEDVR2 = "39:104"
N_AUTO_PROMPT = "41:21"
N_ENHANCER = "41:167"

# Resolutions keep the 2:3-ish portrait default; Moss takes width/height directly
SIZE_PRESETS = {
    "512x768": (512, 768),
    "768x1024": (768, 1024),
    "832x1248": (832, 1248),
    "1024x1024": (1024, 1024),
    "1024x1536": (1024, 1536),
    "1152x1728": (1152, 1728),
    "1536x1024": (1536, 1024),
}

# Aspect ratios offered in the megapixel picker: (label, w/h)
ASPECTS = [
    ("1:1", 1 / 1),
    ("3:4", 3 / 4),
    ("2:3", 2 / 3),
    ("9:16", 9 / 16),
    ("4:3", 4 / 3),
    ("3:2", 3 / 2),
    ("16:9", 16 / 9),
]

# Moss's latent prefers multiples of 16; rounding keeps the graph happy.
GRID = 16


def size_for_megapixels(megapixels: float, aspect: str = "2:3") -> tuple[int, int]:
    """Turn a megapixel budget plus an aspect ratio into pixel dimensions.

    megapixels is the total pixel count in millions (1.0 -> ~1024x1024 worth of
    pixels). The two sides are solved from the target area and the ratio, then
    snapped to the 16-pixel grid Moss expects.
    """
    try:
        mp = float(megapixels)
    except (TypeError, ValueError):
        mp = 1.0
    mp = max(0.25, min(16.0, mp))

    ratio = next((r for label, r in ASPECTS if label == aspect), 2 / 3)
    total_px = mp * 1_000_000

    # width * height = total, width / height = ratio
    h = (total_px / ratio) ** 0.5
    w = h * ratio

    def snap(v: float) -> int:
        return max(GRID * 16, int(round(v / GRID)) * GRID)

    return snap(w), snap(h)



# ---------------------------------------------------------------- LoRA triggers
_LORA_ROOTS = (
    r"E:\Comfy-Desktop\ComfyUI-Shared\models\loras",
    r"E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\loras",
    r"D:\models\loras",
)

_trigger_cache: dict[str, str] = {}
_trigger_scanned = False


def _scan_triggers() -> dict[str, str]:
    """Map lora basename (lower, no extension) -> trigger words.

    A LoRA may ship a sidecar file with the same name: a .json carrying a
    `triggerWords` field, or a plain .txt holding the trigger line. That text has
    to lead the prompt, or the LoRA barely takes effect.
    """
    global _trigger_scanned
    if _trigger_scanned:
        return _trigger_cache
    import json as _json
    for root in _LORA_ROOTS:
        if not os.path.isdir(root):
            continue
        for dp, _dns, fns in os.walk(root):
            for fn in fns:
                low = fn.lower()
                if not low.endswith((".json", ".txt")):
                    continue
                stem = os.path.splitext(low)[0]
                # skip tooling files that are not per-lora metadata
                if stem in ("license", "readme", "merges", "lora_manager_stats"):
                    continue
                fp = os.path.join(dp, fn)
                text = ""
                try:
                    if low.endswith(".json"):
                        d = _json.load(open(fp, encoding="utf-8"))
                        text = str(d.get("triggerWords") or "").strip()
                    else:
                        raw = open(fp, encoding="utf-8", errors="ignore").read().strip()
                        # a txt sidecar is the trigger list itself, one line is enough
                        text = raw.split("\n")[0].strip()
                except Exception:
                    text = ""
                if text and len(text) < 300:
                    _trigger_cache.setdefault(stem, text)
    _trigger_scanned = True
    return _trigger_cache


def trigger_for(name: str) -> str:
    """Trigger words for one LoRA path, or an empty string."""
    stem = os.path.splitext(os.path.basename(name or ""))[0].lower()
    return _scan_triggers().get(stem, "")


def triggers_for(names) -> list[str]:
    """Trigger words for a list of LoRA paths, de-duplicated, in order."""
    out, seen = [], set()
    for n in (names or []):
        t = trigger_for(n)
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def prefix_triggers(prompt: str, names) -> str:
    """Put the LoRA triggers at the very front, joined by commas."""
    trig = triggers_for(names)
    if not trig:
        return prompt
    head = ", ".join(trig)
    body = (prompt or "").strip()
    if body.lower().startswith(head.lower()):
        return body
    return f"{head}, {body}" if body else head


def list_loras_with_triggers() -> list[dict]:
    """The picker list, each entry carrying its trigger words."""
    out = []
    for it in list_loras():
        it = dict(it)
        it["trigger"] = trigger_for(it["name"])
        out.append(it)
    return out


def list_loras() -> list[dict]:
    """LoRAs installed on this ComfyUI, for the picker."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{config.BASE}/models/loras", timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        items = data if isinstance(data, list) else data.get("files", [])
        return [
            {"name": i, "display": os.path.splitext(os.path.basename(i))[0]}
            for i in items
        ]
    except Exception:
        return []


def list_base_models() -> list[dict]:
    """UNET/diffusion checkpoints the Moss graph can be pointed at.

    Only models whose architecture suits the Moss pipeline are useful here; the
    node itself accepts any diffusion model, so the list is every file present
    plus a marker for which one the template ships with.
    """
    import urllib.request
    try:
        with urllib.request.urlopen(f"{config.BASE}/models/diffusion_models", timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        items = data if isinstance(data, list) else data.get("files", [])
    except Exception:
        items = []

    current = ""
    try:
        wf = _load_template()
        if N_UNET in wf:
            current = wf[N_UNET]["inputs"].get("unet_name", "")
    except Exception:
        pass

    out = []
    for i in items:
        out.append({
            "name": i,
            "display": os.path.splitext(os.path.basename(i))[0],
            "default": i == current,
            # The Moss text encoder expects the moss_image family; flag others
            # so the picker can warn rather than silently break the graph.
            "family": ("moss" if "moss" in i.lower()
                       else "qwen" if "qwen" in i.lower()
                       else "krea" if "krea" in i.lower() or "kr2" in i.lower()
                       else "other"),
        })
    return out


def list_system_prompts() -> list[dict]:
    """The prompt-writer system prompts shipped with the Qwen enhancer node."""
    prompt_dir = (
        r"E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\custom_nodes"
        r"\comfyui-qwen-image21-enhancer\prompt_files"
    )
    if not os.path.isdir(prompt_dir):
        return []
    out = []
    for name in sorted(os.listdir(prompt_dir)):
        if not name.endswith(".txt"):
            continue
        path = os.path.join(prompt_dir, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception:
            continue
        out.append({"name": name, "path": path, "content": content})
    return out


def normalize_loras(picks) -> list[dict]:
    """Turn whatever the UI sends into the AUSBOSS lora entry shape.

    Accepts {"name", "strength", "enabled"} dicts, or "path::weight" strings.
    Strength is clamped to the range the sliders in ComfyUI expose.
    """
    out = []
    for p in picks or []:
        if isinstance(p, str):
            path, _, w = p.partition("::")
            try:
                strength = float(w) if w else 1.0
            except ValueError:
                strength = 1.0
            name = path
        elif isinstance(p, dict):
            name = p.get("name") or p.get("lora_name") or ""
            try:
                strength = float(p.get("strength", 1.0))
            except (TypeError, ValueError):
                strength = 1.0
            if p.get("enabled") is False:
                continue
        else:
            continue
        if not name:
            continue
        strength = max(-4.0, min(4.0, strength))
        out.append({
            "id": name,
            "name": name,
            "strength": strength,
            "strength_clip": strength,
            "enabled": True,
            "triggers": "",
        })
    return out


# Framing folder names, keyed by the composition mode the user picked.
_FRAME_DIR = {
    "front_back": "正反",
    "headshot_plus_front_back": "正反",
    "headshot": "大头",
    "half_body": "半身",
    "full_body": "全身",
    "natural_action": "全身",
}


def _save_prefix(composition: str = "", view: str = "") -> str:
    """正反面和大头/<framing> — a subfolder under output_dir (1图片),
    so the final path is:
    E:\\Comfy-Desktop\\ComfyUI-Shared\\output\\1图片\\正反面和大头\\
    The framing name survives as the filename stem (正反_832x1248_00001.png)
    so a folder of mixed shots stays readable."""
    frame = _FRAME_DIR.get((composition or "").strip(), "")
    if not frame:
        frame = {"front": "正面", "back": "背面", "side": "侧面"}.get(
            (view or "").strip(), "正反")
    return f"正反面和大头/{frame}"

def build(
    prompt: str,
    negative: str = "",
    seed: int = -1,
    width: int = 832,
    height: int = 1248,
    loras: list[dict] | None = None,
    enable_seedvr2: bool = False,   # no upscaler in this graph; kept for API compat
    enable_auto_prompt: bool = False,
    enable_layout: bool = False,
    base_model: str = "",
    composition: str = "",
    view: str = "",
    steps: int = 0,
    cfg: float = 0.0,
    sampler: str = "",
    scheduler: str = "",
) -> dict:
    """Copy the template and patch the per-draw values."""
    wf = copy.deepcopy(_load_template())

    if base_model and N_UNET in wf:
        wf[N_UNET]["inputs"]["unet_name"] = base_model

    if N_TEXT in wf:
        wf[N_TEXT]["inputs"]["text"] = prompt

    if N_SEED in wf:
        wf[N_SEED]["inputs"]["seed"] = int(seed)

    if N_RESOLUTION in wf:
        wf[N_RESOLUTION]["inputs"]["width"] = int(width)
        wf[N_RESOLUTION]["inputs"]["height"] = int(height)
        wf[N_RESOLUTION]["inputs"]["batch_size"] = 1

    if negative and N_NEG in wf:
        wf[N_NEG]["inputs"]["text"] = negative

    picks = normalize_loras(loras)
    if N_LORA in wf:
        if picks:
            wf[N_LORA]["inputs"]["loras"] = json.dumps(picks, ensure_ascii=False)
        else:
            # An empty pick must still switch every template LoRA off, or the
            # graph keeps whatever the file shipped with.
            existing = wf[N_LORA]["inputs"].get("loras", "[]")
            try:
                parsed = json.loads(existing)
            except Exception:
                parsed = []
            for entry in parsed:
                entry["enabled"] = False
            wf[N_LORA]["inputs"]["loras"] = json.dumps(parsed, ensure_ascii=False)

    # ---- sampling overrides -------------------------------------------------
    # Steps and CFG come from switch nodes in the stock graph. Leaving them at
    # 0 keeps the shipped behaviour (34 steps / CFG 3). A non-zero value is
    # wired straight into KSampler, bypassing the switch chain.
    K_SAMPLER = "39:29"
    if K_SAMPLER in wf:
        ks = wf[K_SAMPLER]["inputs"]
        if steps and int(steps) > 0:
            ks["steps"] = int(steps)
        if cfg and float(cfg) > 0:
            ks["cfg"] = float(cfg)
        if sampler:
            ks["sampler_name"] = sampler
        if scheduler:
            ks["scheduler"] = scheduler

    if N_SEEDVR2 in wf:
        # CFG 3 — the switch picks 39:102 (cfg 3) over 39:103 (cfg 1). Guidance
        # costs a second model pass per step, so this is the slow-but-faithful
        # setting; it used to be forced to 1 by the (nonexistent) SeedVR2 flag.
        wf[N_SEEDVR2]["inputs"]["switch"] = True

    if N_AUTO_PROMPT in wf:
        wf[N_AUTO_PROMPT]["inputs"]["switch"] = bool(enable_auto_prompt)

    # Setting the switch alone is not enough: the enhancer node stays wired to the
    # switch's on_true input, and ComfyUI executes every reachable node whether or
    # not its output is selected. That call costs ~90s per image. Bypass the node
    # itself (mode 4) when the enhancer is off, so the graph skips it entirely.
    # The two switches that read the enhancer must also be told to use the raw
    # prompt, which they already do via on_false -> 153.
    if N_ENHANCER in wf:
        wf[N_ENHANCER]["mode"] = 0 if enable_auto_prompt else 4
    for sid in ("41:91", "41:92"):
        if sid in wf:
            wf[sid]["inputs"]["switch"] = False

    if N_SAVE in wf:
        # The user fixed the destination (new ComfyUI Desktop install):
        #   E:\Comfy-Desktop\ComfyUI-Shared\output\1图片\正反面和大头
        # output_dir is a subfolder of ComfyUI's output root (the node refuses
        # rooted paths); the prefix adds the framing subfolder and the file
        # stem, e.g. 正反_832x1248_00001.png.
        wf[N_SAVE]["inputs"]["output_dir"] = "1图片"
        wf[N_SAVE]["inputs"]["filename_prefix"] = _save_prefix(composition, view)

    return wf


def validate(wf: dict) -> list[str]:
    """Report links pointing at nodes or slots that do not exist."""
    problems = []
    for nid, node in wf.items():
        for key, val in (node.get("inputs") or {}).items():
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                target = val[0]
                if target not in wf:
                    problems.append(f"{nid}.{key} -> missing node {target}")
    return problems


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    wf = build("test prompt", seed=42)
    print("nodes:", len(wf))
    probs = validate(wf)
    print("broken links:", len(probs))
    for p in probs[:10]:
        print("  ", p)
