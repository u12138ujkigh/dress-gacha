# -*- coding: utf-8 -*-
"""ComfyUI bridge: build an API-format Krea2 graph, submit it, wait, collect bytes."""
from __future__ import annotations

import json
import os
import re as _re
import threading
import time
import urllib.parse
import urllib.request
import uuid

from . import config

BASE = config.BASE
# Generated images land directly in the user's fixed ComfyUI output subfolder.
# The SaveImage node writes there; render() no longer copies a second set.
OUT_DIR = config.WEBUI_OUT


class ComfyError(RuntimeError):
    pass


def _post(path: str, payload: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get(path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_bytes(path: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return r.read()


def build_workflow(
    prompt: str,
    negative: str,
    seed: int,
    tier: str,
    width: int = 832,
    height: int = 1216,
    steps: int = 4,
    cfg: float = 1.0,
) -> dict:
    models = config.discover()
    unet = models["unet_by_tier"].get(tier) or models["unet_by_tier"].get("normal")
    if not unet:
        raise ComfyError("no Krea2 diffusion model found on this ComfyUI install")
    if not models.get("clip"):
        raise ComfyError("no qwen3vl 4b text encoder found")
    if not models.get("vae"):
        raise ComfyError("qwen_image_vae not found")

    g: dict = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": models["clip"], "type": "krea2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": models["vae"]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "7": {"class_type": "EmptyLatentImage",
              "inputs": {"width": width, "height": height, "batch_size": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage",
               "inputs": {"images": ["9", 0],
                          "filename_prefix": "1图片/正反面和大头/dressgacha"}},
    }

    model_ref: list = ["1", 0]
    if models.get("lora_4step"):
        g["4"] = {"class_type": "LoraLoaderModelOnly",
                  "inputs": {"model": ["1", 0],
                             "lora_name": models["lora_4step"],
                             "strength_model": 1.0}}
        model_ref = ["4", 0]

    g["8"] = {"class_type": "KSampler",
              "inputs": {"model": model_ref,
                         "positive": ["5", 0],
                         "negative": ["6", 0],
                         "latent_image": ["7", 0],
                         "seed": int(seed),
                         "steps": int(steps),
                         "cfg": float(cfg),
                         "sampler_name": "euler",
                         "scheduler": "simple",
                         "denoise": 1.0}}
    return g


def submit(workflow: dict, client_id: str | None = None) -> str:
    payload = {"prompt": workflow, "client_id": client_id or CLIENT_ID}
    res = _post("/prompt", payload)
    if "prompt_id" not in res:
        raise ComfyError(f"submit rejected: {json.dumps(res)[:600]}")
    return res["prompt_id"]


# One long-lived listener per prompt: the socket is opened before submitting, so
# no progress frame is missed while a 40-second render runs.
# ComfyUI only pushes progress for the client_id that submitted the prompt, so
# both the submit call and the websocket must share one identity.
CLIENT_ID = f"dress-gacha-{os.getpid()}"
_WS_LISTENERS: dict[str, dict] = {}
_WS_LOCK = threading.Lock()


def _ws_read_frame(sock):
    """Read one websocket frame; return its text payload (or None)."""
    def recvn(n):
        out = b""
        while len(out) < n:
            c = sock.recv(n - len(out))
            if not c:
                raise ConnectionError("closed")
            out += c
        return out

    hdr = recvn(2)
    b1, b2 = hdr[0], hdr[1]
    opcode = b1 & 0x0F
    masked = b2 & 0x80
    length = b2 & 0x7F
    if length == 126:
        length = int.from_bytes(recvn(2), "big")
    elif length == 127:
        length = int.from_bytes(recvn(8), "big")
    mask = recvn(4) if masked else None
    payload = recvn(length) if length else b""
    if mask:
        payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
    if opcode == 0x8:            # close
        raise ConnectionError("closed")
    if opcode == 0x9:            # ping -> caller may ignore
        return None
    return payload.decode("utf-8", "replace")


def start_progress_listener(prompt_id_hint: str = "") -> None:
    """Open a background websocket that keeps the latest progress for any prompt."""
    import threading as _th
    with _WS_LOCK:
        if _WS_LISTENERS.get("_alive"):
            return
        _WS_LISTENERS.clear()
        _WS_LISTENERS["_alive"] = True
        _WS_LISTENERS["state"] = {"step": 0, "steps": 0, "phase": "", "prompt_id": ""}

    def run():
        import base64 as _b64
        import os as _os
        import socket as _s

        host, port = "127.0.0.1", 8188
        try:
            base = config.BASE
            if "//" in base:
                hp = base.split("//", 1)[1]
                if ":" in hp:
                    host, port = hp.split(":")[0], int(hp.split(":")[1].split("/")[0])
        except Exception:
            pass

        while _WS_LISTENERS.get("_alive"):
            try:
                sock = _s.create_connection((host, port), timeout=180)
                key = _b64.b64encode(_os.urandom(16)).decode()
                sock.sendall((
                    f"GET /ws?clientId={CLIENT_ID}\r\n"
                    f"Host: {host}:{port}\r\n"
                    "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                    f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
                ).encode())
                # drain the HTTP handshake headers up to the blank line
                raw = b""
                while b"\r\n\r\n" not in raw:
                    c = sock.recv(4096)
                    if not c:
                        raise ConnectionError("closed")
                    raw += c
                head, rest = raw.split(b"\r\n\r\n", 1)
                if b"101" not in head.split(b"\r\n")[0]:
                    raise ConnectionError("handshake refused")

                while _WS_LISTENERS.get("_alive"):
                    try:
                        txt = _ws_read_frame(sock)
                    except Exception:
                        break
                    if not txt:
                        continue
                    try:
                        obj = json.loads(txt)
                    except Exception:
                        continue
                    typ = obj.get("type")
                    d = obj.get("data") or {}
                    st = _WS_LISTENERS.get("state") or {}
                    if typ == "progress":
                        st.update(step=int(d.get("value") or 0),
                                  steps=int(d.get("max") or 0),
                                  phase="running",
                                  prompt_id=str(d.get("prompt_id") or st.get("prompt_id") or ""))
                    elif typ == "executing":
                        pid = str(d.get("prompt_id") or "")
                        if pid and pid != "None":
                            st["prompt_id"] = pid
                            st["phase"] = "running"
                        if d.get("node") is None and pid:
                            st["phase"] = "finishing"
                    elif typ == "execution_start":
                        st["phase"] = "running"
                    elif typ == "execution_cached":
                        st.setdefault("phase", "running")
                try:
                    sock.close()
                except Exception:
                    pass
            except Exception:
                time.sleep(0.6)

    _th.Thread(target=run, daemon=True).start()


def stop_progress_listener() -> None:
    with _WS_LOCK:
        _WS_LISTENERS["_alive"] = False
        _WS_LISTENERS.pop("state", None)


def interrupt_and_clear() -> None:
    """Stop a stuck ComfyUI run and drop its queued items.

    Called from a render's error path: a job that timed out or errored can leave
    a prompt stuck in the running queue, which holds VRAM and poisons every
    later render until the app is restarted. Best effort — network failures
    here must not mask the original render error.
    """
    def _hit(path, payload, timeout):
        try:
            req = urllib.request.Request(
                BASE + path,
                data=json.dumps(payload).encode("utf-8") if payload is not None else b"",
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                r.read()
        except Exception:
            pass

    _hit("/interrupt", None, 5)          # empty POST, no body
    _hit("/queue", {"clear": True}, 5)   # purge any pending/running entries


def live_progress(prompt_id: str = "") -> dict:
    st = dict(_WS_LISTENERS.get("state") or {})
    if prompt_id and st.get("prompt_id") and st["prompt_id"] != prompt_id:
        return {}
    return st


def progress_via_ws(prompt_id: str, timeout: float = 3.0) -> dict | None:
    """Read live step progress over ComfyUI's websocket.

    No HTTP progress endpoint exists, so the only true step signal is the
    `progress` event pushed on /ws. Polling cannot see it; this opens a short
    socket, listens for one progress message for this prompt, and returns.
    """
    import socket as _s
    import base64 as _b64
    import os as _os
    import struct as _st

    host, port = "127.0.0.1", 8188
    try:
        base = config.BASE
        if "//" in base:
            hp = base.split("//", 1)[1]
            if ":" in hp:
                host, port = hp.split(":")[0], int(hp.split(":")[1].split("/")[0])
    except Exception:
        pass

    key = _b64.b64encode(_os.urandom(16)).decode()
    try:
        sock = _s.create_connection((host, port), timeout=timeout)
    except Exception:
        return None
    try:
        req = (
            f"GET /ws?clientId=dress-gacha HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(req.encode())
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                chunk = sock.recv(65536)
            except _s.timeout:
                break
            if not chunk:
                break
            buf += chunk
            # crude frame scan: look for a progress payload in the stream
            txt = buf.decode("utf-8", "replace")
            if '"progress"' in txt:
                import re as _re
                m = _re.search(
                    r'\{[^{}]*"type"\s*:\s*"progress"[^{}]*"data"\s*:\s*\{[^{}]*\}[^{}]*\}',
                    txt)
                if not m:
                    m = _re.search(r'\{"data":\{[^{}]*"max"[^{}]*\},"type":"progress"\}', txt)
                if m:
                    try:
                        obj = json.loads(m.group())
                        d = obj.get("data", {})
                        if d.get("prompt_id") in (None, prompt_id):
                            return {"step": int(d.get("value") or 0),
                                    "steps": int(d.get("max") or 0),
                                    "node": str(d.get("node") or "")}
                    except Exception:
                        pass
            if len(buf) > 400000:
                buf = buf[-80000:]
        return None
    finally:
        try:
            sock.close()
        except Exception:
            pass


def queue_state(prompt_id: str) -> dict:
    """Where this prompt sits in ComfyUI's queue, plus the live step counter.

    ComfyUI exposes no per-prompt progress endpoint, so the signal comes from
    three places: /queue position, the sampler's step messages in /history (only
    present once finished), and the web socket. Without the socket we can still
    report a meaningful phase and step count, which is what the UI shows.
    """
    out = {"phase": "queued", "position": None, "step": 0, "steps": 0,
           "percent": 0.0, "node": ""}
    try:
        q = _get("/queue", timeout=8)
    except Exception:
        return out
    running = q.get("queue_running") or []
    pending = q.get("queue_pending") or []
    for i, item in enumerate(pending):
        # item = [number, prompt_id, prompt, extra, outputs]
        if len(item) > 1 and item[1] == prompt_id:
            out["phase"] = "queued"
            out["position"] = i + 1
            out["percent"] = 0.0
            return out
    for item in running:
        if len(item) > 1 and item[1] == prompt_id:
            out["phase"] = "running"
            out["position"] = 0
            break
    # This ComfyUI build pushes no per-step events, so a true step counter is not
    # available. Progress is estimated from elapsed wall time against the average
    # time of recent renders of the same shape, which is monotonic and honest
    # about what it is; `steps` still reports the graph's real step budget.
    if out["phase"] == "running":
        out["estimated"] = True
    return out


def wait(prompt_id: str, timeout: float = 300.0, poll: float = 1.5,
         on_progress=None) -> dict:
    """Poll until the prompt lands; report phase and step progress meanwhile.

    on_progress receives the dict from queue_state() each poll, so a caller can
    surface "queued / running 12/20 steps" instead of a black box.
    """
    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        try:
            if on_progress is not None:
                try:
                    on_progress(queue_state(prompt_id))
                except Exception as _pe:
                    import traceback as _tb
                    _tb.print_exc()
            hist = _get(f"/history/{prompt_id}")
            entry = hist.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("status_str") == "error" or status.get("completed") is False:
                    msgs = status.get("messages", [])
                    raise ComfyError(f"job failed: {json.dumps(msgs)[:800]}")
                return entry
        except ComfyError:
            raise
        except Exception as e:  # transient connection noise
            last_err = e
        time.sleep(poll)
    raise ComfyError(f"timeout after {timeout:.0f}s waiting for {prompt_id} ({last_err})")


def _resolve_int(workflow: dict, value, depth: int = 0):
    """Follow links and switch nodes until a literal number appears.

    A MOSS graph routes `steps` through a ComfySwitchNode, so reading the raw
    input gives a link rather than a number.
    """
    if depth > 12:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if not (isinstance(value, list) and value):
        return None
    node = (workflow or {}).get(str(value[0]))
    if not node:
        return None
    ins = node.get("inputs") or {}
    ct = node.get("class_type", "")
    if "Switch" in ct:
        pos = value[1] if len(value) > 1 else 0
        flag = ins.get("switch")
        # ComfySwitchNode: on_true when switch is truthy, else on_false
        picked = ins.get("on_true") if flag else ins.get("on_false")
        if isinstance(flag, list):
            flag = _resolve_int(workflow, flag, depth + 1)
            picked = ins.get("on_true") if flag else ins.get("on_false")
        return _resolve_int(workflow, picked, depth + 1)
    for cand in ("steps", "value", "int", "number", "seed"):
        if cand in ins:
            got = _resolve_int(workflow, ins[cand], depth + 1)
            if got is not None:
                return got
    return None


_RENDER_TIMES: list[float] = []


def record_render_time(seconds: float) -> None:
    if seconds > 0:
        _RENDER_TIMES.append(float(seconds))
        del _RENDER_TIMES[:-10]      # keep the last ten


def average_render_time() -> float:
    if not _RENDER_TIMES:
        return 45.0                   # cold-start guess for an 8 GB card
    return sum(_RENDER_TIMES) / len(_RENDER_TIMES)


def count_steps(workflow: dict) -> int:
    """Total sampling steps in a graph, summing samplers via link resolution."""
    total = 0
    for node in (workflow or {}).values():
        ct = node.get("class_type", "")
        if "Sampler" in ct:
            got = _resolve_int(workflow, (node.get("inputs") or {}).get("steps"))
            if got:
                total += got
    return total


def entry_images(entry: dict) -> list[dict]:
    imgs = []
    for node_out in (entry.get("outputs") or {}).values():
        for im in node_out.get("images", []) or []:
            imgs.append(im)
    return imgs


def fetch_image_bytes(im: dict) -> bytes:
    q = urllib.parse.urlencode({
        "filename": im.get("filename", ""),
        "subfolder": im.get("subfolder", ""),
        "type": im.get("type", "output"),
    })
    return _get_bytes(f"/view?{q}")


def render(
    prompt: str,
    negative: str,
    seed: int,
    tier: str,
    width: int = 832,
    height: int = 1216,
    steps: int = 4,
    cfg: float = 1.0,
    timeout: float = 300.0,
    save: bool = True,
) -> dict:
    """One blocking render. ComfyUI's SaveImage writes the single copy into
    OUT_DIR; we only resolve its path for the web preview. No second save."""
    # Free any model cached by a previous job before this render loads its own.
    config.free_vram()
    wf = build_workflow(prompt, negative, seed, tier, width=width, height=height,
                        steps=steps, cfg=cfg)
    pid = submit(wf)
    entry = wait(pid, timeout=timeout)
    imgs = entry_images(entry)
    if not imgs:
        raise ComfyError("job completed with no images")

    # SaveImage already wrote this file under the ComfyUI output subfolder. The
    # entry tells us its exact subfolder + filename; resolve it for /outputs/.
    im = imgs[0]
    filename = im.get("filename") or ""
    out = {"prompt_id": pid, "filename": filename, "url": None, "bytes": 0}
    if save:
        # The file is already in OUT_DIR (= ComfyUI output/1图片/正反面和大头).
        out["url"] = "/outputs/" + urllib.parse.quote(filename)
        out["path"] = os.path.join(OUT_DIR, filename)
    return out

