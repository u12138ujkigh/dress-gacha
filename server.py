# -*- coding: utf-8 -*-
"""dress-gacha server: zero-dependency HTTP on 127.0.0.1.

Endpoints
    GET  /                    the WebUI
    GET  /api/health          ComfyUI + model + lexicon status
    GET  /api/lexicon         tiers, styles, combination counts
    POST /api/draw            roll prompts only
    POST /api/render          roll + render through ComfyUI (background queue)
    GET  /api/job/<id>        batch render progress
    GET  /outputs/<file>      generated images
    GET  /api/img?prompt=...  one-off render (sync, used by the single-shot button)
"""
from __future__ import annotations

import json
import urllib.request
import mimetypes
import os
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, quote

from engine import comfy, config, composer, api_writer, moss_workflow
from engine import design, taxonomy
from engine import applog

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
# 生成的图片由 ComfyUI 的 SaveImage 节点直接落到这个真实目录；WebUI 预览、
# 删除都读写同一处，不再复制第二份。可用 DRESS_GACHA_OUT 覆盖。
OUT = config.WEBUI_OUT
HOST = "127.0.0.1"
PORT = int(os.environ.get("DRESS_GACHA_PORT", "8770"))

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
RENDER_LOCK = threading.Lock()  # one render at a time: 8 GB VRAM
CANCEL_FLAG = threading.Event()
PROGRESS: dict[str, dict] = {}
PROGRESS_LOCK = threading.Lock()
RENDER_JOBS: dict[str, dict] = {}
RENDER_JOBS_LOCK = threading.Lock()
# A render job is "abandoned" when the browser stops polling it: either the
# worker hung inside comfy.wait() or the tab/request died. Without a staleness
# rule one such job stays "running" forever, every later /api/render_async is
# rejected with 429, and only a full restart clears the in-memory dict — the
# exact "two images then everything fails until I reopen the app" symptom.
RENDER_STALE_AFTER = 40.0     # seconds without a status poll -> abandoned
RENDER_START_GRACE = 20.0     # grace for a just-submitted job (before first poll)
SERVER = None  # set in main(); /api/quit uses it to shut the loop down

# The WebUI app window pings /api/heartbeat every few seconds. If those pings
# stop for good (window closed), the daemon below exits the server so no
# orphaned backend is left running. A page refresh only interrupts pings for a
# second or two, well under the timeout, so it never trips the shutdown.
HEARTBEAT = {"t": 0.0, "seen": False}
HEARTBEAT_LOCK = threading.Lock()
HEARTBEAT_TIMEOUT = 12.0  # seconds with no ping -> assume the window was closed


def state_busy_render() -> bool:
    """Is a *live* render still running?

    A job whose status has not been polled for RENDER_STALE_AFTER seconds is
    abandoned (worker hung, or browser navigated away / request timed out).
    Such a job must not block every future render forever. Drop it here and
    free the slot; the real GPU work is still serialised by config.GPU_LANE_LOCK,
    so this cannot cause two renders to overlap.
    """
    now = time.time()
    stale = []
    busy = False
    with RENDER_JOBS_LOCK:
        for jid, j in RENDER_JOBS.items():
            if j.get("status") != "running":
                continue
            seen = j.get("last_seen") or j.get("started") or 0
            if now - seen > RENDER_STALE_AFTER and now - j.get("started", 0) > RENDER_START_GRACE:
                stale.append(jid)
        for jid in stale:
            RENDER_JOBS.pop(jid, None)
        busy = any(j.get("status") == "running" for j in RENDER_JOBS.values())
    # Never leave a half-dead ComfyUI run holding VRAM for the next job.
    if stale:
        config.free_vram()
    return busy


def _cancel_comfy_work() -> dict:
    """Stop whatever ComfyUI is doing: clear the queue, interrupt the runner.

    Runs in a worker thread with its own deadline: ComfyUI's /interrupt blocks
    while nothing is executing, and a cancel request must return promptly anyway.
    """
    import urllib.request as _u
    CANCEL_FLAG.set()
    out = {}

    def hit(path, payload=None):
        url = config.BASE + path
        try:
            if payload is None:
                req = _u.Request(url, method="POST")
            else:
                req = _u.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
            with _u.urlopen(req, timeout=3) as r:
                return r.status
        except Exception as e:
            return str(e)[:60]

    def worker():
        out["interrupt"] = hit("/interrupt")
        out["queue_clear"] = hit("/queue", {"clear": True})

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(timeout=5)              # never hold the HTTP response longer than this
    if th.is_alive():
        out.setdefault("interrupt", "timeout")
    return out


def _job_new(total: int, tier: str, style: str) -> dict:
    jid = uuid.uuid4().hex[:12]
    job = {
        "id": jid,
        "total": total,
        "done": 0,
        "status": "running",
        "tier": tier,
        "style": style,
        "started": time.time(),
        "items": [],
        "error": None,
    }
    with JOBS_LOCK:
        JOBS[jid] = job
    return job


def _job_public(job: dict) -> dict:
    return {
        "id": job["id"],
        "total": job["total"],
        "done": job["done"],
        "status": job["status"],
        "tier": job["tier"],
        "style": job["style"],
        "elapsed": round(time.time() - job["started"], 1),
        "items": job["items"],
        "error": job["error"],
    }


def _render_worker(job: dict, draws: list[dict], width: int, height: int, steps: int,
                   triggers: str = "") -> None:
    for d in draws:
        if CANCEL_FLAG.is_set():
            with JOBS_LOCK:
                job["status"] = "cancelled"
            return
        try:
            # GPU lock outermost (GPU -> RENDER order, matches render_moss_blocking)
            # so a comfy: write can never swap a text model in mid-render.
            with config.GPU_LANE_LOCK, RENDER_LOCK:
                res = comfy.render(
                    # The manual trigger words go at the end of the prompt on
                    # this path too, so they apply whether or not a LoRA was
                    # picked.
                    prompt=append_lora_triggers(d["prompt"], triggers),
                    negative=d["negative"],
                    seed=d["seed"],
                    tier=d["tier"],
                    width=width,
                    height=height,
                    steps=steps,
                )
            item = dict(d)
            item["image"] = res.get("url")
            item["prompt_id"] = res.get("prompt_id")
        except Exception as e:
            item = dict(d)
            item["image"] = None
            item["error"] = str(e)[:400]
        with JOBS_LOCK:
            job["items"].append(item)
            job["done"] = len(job["items"])
    with JOBS_LOCK:
        job["status"] = "done"



def _norm_think(v) -> str:
    """Normalise the 思考强度 value from the client: legacy true/false booleans
    and strings all collapse to one of off/on/low/medium/high."""
    if v is None:
        return "off"
    if isinstance(v, bool):
        return "on" if v else "off"
    s = str(v).strip().lower()
    return s if s in ("off", "on", "low", "medium", "high") else "off"


def _safe(fn, *args, **kwargs):
    """Run fn and swallow everything — for fire-and-forget background work."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def append_lora_triggers(prompt: str, triggers: str) -> str:
    """Append manual LoRA triggers after the finished API prompt.

    Sidecar trigger words are still prefixed from the selected LoRA files; this
    separate user-written field belongs at the end, where it can extend rather
    than replace the model's design.
    """
    base = (prompt or "").rstrip()
    extra = (triggers or "").strip()
    if not extra:
        return base
    if not base:
        return extra
    # An English comma already carries the separator; a Chinese one is
    # full-width and takes no space after it.
    if base.endswith(","):
        return base + " " + extra
    if base.endswith("，"):
        return base + extra
    return base + ", " + extra


@config.serialize_gpu
def render_moss_blocking(body: dict) -> dict:
    """Run one MOSS render and return {image, prompt_id, bytes, steps}.

    Raises on failure: the HTTP route maps ValueError to 400 and anything else
    to 502, while the async worker stores the message on the job.
    """
    body = body or {}
    prompt = body.get("prompt", "")
    negative = body.get("negative", "")
    seed = _opt_int_plain(body.get("seed"))
    seed = -1 if seed is None else seed
    width = _opt_int_plain(body.get("width"))
    height = _opt_int_plain(body.get("height"))

    # A megapixel budget plus an aspect ratio overrides explicit sizes.
    mp = body.get("megapixels")
    aspect = body.get("aspect", "2:3")
    if mp not in (None, "", "null"):
        try:
            width, height = moss_workflow.size_for_megapixels(float(mp), aspect)
        except (TypeError, ValueError):
            pass
    width = width or 832
    height = height or 1248

    loras = body.get("loras") or []
    # A LoRA's trigger words lead the prompt, or it barely takes effect. They are
    # collected from the enabled LoRAs only, de-duplicated, comma-joined.
    if loras:
        _names = [l.get("name") or l.get("lora") or ""
                  for l in loras if isinstance(l, dict) and l.get("enabled", True)]
        prompt = moss_workflow.prefix_triggers(prompt, _names)
    enable_seedvr2 = bool(body.get("enable_seedvr2"))
    enable_auto_prompt = bool(body.get("enable_auto_prompt"))
    enable_layout = bool(body.get("enable_layout"))
    base_model = body.get("base_model") or ""
    # Optional sampling overrides. 0 means "keep the workflow defaults"
    # (34 steps / CFG 3 / euler / simple).
    steps = body.get("steps") or 0
    cfg = body.get("cfg") or 0.0
    sampler = body.get("sampler") or ""
    scheduler = body.get("scheduler") or ""

    if not prompt.strip():
        raise ValueError("prompt is empty")

    prompt = append_lora_triggers(prompt, body.get("lora_triggers", ""))

    wf = moss_workflow.build(
        prompt=prompt,
        negative=negative,
        seed=seed,
        width=width,
        height=height,
        loras=loras,
        enable_seedvr2=enable_seedvr2,
        enable_auto_prompt=enable_auto_prompt,
        enable_layout=enable_layout,
        base_model=base_model,
        # Folder for the saved image: Moss/<date>/<framing>
        composition=body.get("composition", "") or "",
        view=body.get("view", "") or "",
        steps=steps,
        cfg=cfg,
        sampler=sampler,
        scheduler=scheduler,
    )
    broken = moss_workflow.validate(wf)
    if broken:
        raise comfy.ComfyError("workflow has broken links: " + "; ".join(broken[:5]))

    total_steps = comfy.count_steps(wf)
    prog = {"phase": "waiting", "step": 0, "steps": total_steps,
            "percent": 0.0, "position": None, "prompt_id": ""}
    t_start = time.time()

    def on_progress(st):
        prog.update({k: v for k, v in st.items() if v not in (None, "")})
        if not prog.get("steps"):
            prog["steps"] = total_steps
        elapsed = time.time() - t_start
        est = comfy.average_render_time()
        pct = min(97.0, elapsed / max(1.0, est) * 100.0)
        prog["percent"] = round(pct, 1)
        prog["elapsed"] = round(elapsed, 1)
        prog["eta"] = max(0, round(est - elapsed, 1))
        if total_steps:
            prog["step"] = min(total_steps, int(total_steps * pct / 100.0))
        with PROGRESS_LOCK:
            PROGRESS["render"] = dict(prog)

    # The lock guards the GPU submit only; holding it across the wait would
    # block every other render endpoint for up to the job timeout. @serialize_gpu
    # still owns the GPU for the whole submit→wait→collect lifetime.
    pid = ""
    try:
        with RENDER_LOCK:
            if CANCEL_FLAG.is_set():
                CANCEL_FLAG.clear()
            # Free any model left cached by a prior render/write before this one
            # loads its own — no stale VRAM/RAM model is kept between jobs.
            config.free_vram()
            comfy.start_progress_listener()
            time.sleep(0.4)
            pid = comfy.submit(wf)
        prog["prompt_id"] = pid
        prog["phase"] = "running"
        with PROGRESS_LOCK:
            PROGRESS["render"] = dict(prog)

        entry = comfy.wait(pid, timeout=420, on_progress=on_progress, poll=1.0)
        comfy.record_render_time(time.time() - t_start)
        prog.update(phase="saving", percent=99.0, step=prog.get("steps") or 0)
        with PROGRESS_LOCK:
            PROGRESS["render"] = dict(prog)

        imgs = comfy.entry_images(entry)
        if not imgs:
            raise comfy.ComfyError("job finished with no images")
    except Exception:
        # A failed/timed-out job must NOT leave a stuck prompt in ComfyUI's
        # running queue or a cached model holding VRAM. That is what poisoned
        # every render after the first two until the app was restarted.
        if pid:
            try:
                comfy.interrupt_and_clear()
            except Exception:
                traceback.print_exc()
        with PROGRESS_LOCK:
            PROGRESS["render"] = {"phase": "error", "percent": 0.0,
                                  "step": 0, "steps": total_steps,
                                  "prompt_id": pid}
        raise
    finally:
        # Always stop the listener and drop cached models, on success AND on
        # failure — including the CANCEL_FLAG / broken-workflow early paths.
        try:
            comfy.stop_progress_listener()
        except Exception:
            traceback.print_exc()
        try:
            config.free_vram()
        except Exception:
            traceback.print_exc()

    # The workflow's SaveImage already wrote the only copy into OUT. Do not
    # fetch-and-save a second one — that was the duplicate the user spotted.
    name = imgs[0].get("filename") or ""
    with PROGRESS_LOCK:
        PROGRESS["render"] = {"phase": "done", "percent": 100.0,
                              "step": prog.get("steps") or 0,
                              "steps": prog.get("steps") or 0,
                              "prompt_id": pid}
    return {"image": "/outputs/" + quote(name), "prompt_id": pid,
            "bytes": 0, "steps": prog.get("steps")}


def _opt_int_plain(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def guard(route_fn):
    """请求级异常兜底：任何 handler 漏出的异常都写 app.log，不再静默消失。

    从 pythonw 无控制台启动时，BaseHTTPRequestHandler 默认只往 stderr 打印，
    用户看不到 —— 这正是过去"打不开/没反应"难排查的原因。这里统一落盘。
    """
    def _wrapped(self, *args, **kwargs):
        try:
            return route_fn(self, *args, **kwargs)
        except (BrokenPipeError, ConnectionResetError):
            return None   # 客户端断开，属正常，不记日志
        except Exception as exc:
            applog.log_exc("HTTP %s %s" % (getattr(self, "command", "?"), self.path), exc)
            try:
                self._json({"ok": False, "error": str(exc)[:200]}, 500)
            except Exception:
                pass
            return None
    return _wrapped


class Handler(BaseHTTPRequestHandler):
    server_version = "dress-gacha/1.0"
    # HTTP/1.0 closes the socket after every response, which keeps a browser
    # from holding a pooled connection that a restarted server has dropped.
    protocol_version = "HTTP/1.0"
    timeout = 60

    def log_message(self, fmt, *args):  # quieter console
        if "/api/job/" in self.path:
            return
        print(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {fmt % args}")

    # ---------------------------------------------------------------- helpers
    def _json(self, obj, code: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        # Never let a client pool the socket: after a server restart a pooled
        # connection points at a dead process and the next request hangs.
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def _file(self, path: str):
        if not os.path.isfile(path):
            self._json({"error": "not found", "path": path}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            parsed = json.loads(raw.decode("utf-8-sig"))
        except Exception as e:
            raise ValueError(f"body is not valid JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise ValueError("body must be a JSON object")
        return parsed

    @staticmethod
    def _opt_int(v):
        """Accept 42 / "42" / null / "" and return int or None."""
        if v is None or v == "" or v == "null":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    # ---------------------------------------------------------------- routes
    @guard
    def do_GET(self):
        u = urlparse(self.path)
        p = u.path

        if p == "/" or p == "/index.html":
            self._file(os.path.join(WEB, "index.html"))
            return
        if p.startswith("/outputs/"):
            from urllib.parse import unquote
            name = os.path.basename(unquote(p))
            self._file(os.path.join(OUT, name))
            return
        if p.startswith("/web/"):
            rel = os.path.normpath(p[len("/web/"):]).lstrip("\\/")
            self._file(os.path.join(WEB, rel))
            return
        if p == "/api/heartbeat":
            # GET form (used by the WebUI window keepalive). POST also accepted
            # below; both just refresh the timestamp.
            with HEARTBEAT_LOCK:
                HEARTBEAT["t"] = time.time()
                HEARTBEAT["seen"] = True
            self._json({"ok": True})
            return
        if p == "/api/health":
            self._health()
            return
        if p == "/api/think_levels":
            # 思考强度挡位 per model, probed from the model's own backend
            # (ComfyUI object_info / Ollama capabilities / cloud effort ladder).
            model = (parse_qs(u.query).get("model") or [""])[0]
            try:
                levels = api_writer.think_levels(model)
            except Exception:
                levels = ["off", "on"]
            self._json({"model": model, "levels": levels})
            return
        if p == "/api/lexicon":
            self._json(composer.matrix_stats())
            return
        if p.startswith("/api/job/"):
            jid = p[len("/api/job/"):]
            with JOBS_LOCK:
                job = JOBS.get(jid)
                if not job:
                    self._json({"error": "no such job"}, 404)
                    return
                self._json(_job_public(job))
            return
        if p == "/api/img":
            self._one_off(u.query)
            return
        if p == "/api/models":
            try:
                force = "force=1" in (u.query or "")
                if force:
                    models = api_writer.probe_models()
                else:
                    models = api_writer.list_with_status()
                    api_writer.start_probe_async()
                self._json({
                    "models": models,
                    "count": len(models),
                    "probe": api_writer.probe_state(),
                })
            except Exception as e:
                self._json({"error": str(e)}, 502)
            return
        if p == "/api/system_prompts":
            prompts = moss_workflow.list_system_prompts()
            self._json({"prompts": [{"name": p["name"], "chars": len(p["content"])} for p in prompts]})
            return
        if p == "/api/design_methods":
            out = []
            for tier, fname in design.TIER_FILES.items():
                path = os.path.join(design.DESIGN_DIR, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    size = 0
                out.append({
                    "tier": tier,
                    "file": fname,
                    "zh": design.TIER_META[tier]["zh"],
                    "color": design.TIER_META[tier]["color"],
                    "desc": design.TIER_META[tier]["desc"],
                    "chars": size,
                })
            self._json({"methods": out})
            return
        if p == "/api/design_method":
            q = parse_qs(u.query or "")
            tier = (q.get("tier") or [""])[0]
            fname = design.TIER_FILES.get(tier)
            if not fname:
                self._json({"error": f"未知档位：{tier}"}, 400)
                return
            path = os.path.join(design.DESIGN_DIR, fname)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except OSError as e:
                self._json({"error": f"读取失败：{e}"}, 500)
                return
            self._json({
                "tier": tier,
                "file": fname,
                "path": path,
                "zh": design.TIER_META[tier]["zh"],
                "chars": len(text),
                "text": text,
            })
            return
        if p == "/api/styles":
            # Full taxonomy (what API mode can design) plus the pruned tree the
            # lexicon mode can actually draw from.
            self._json({
                "tree": taxonomy.as_tree(),
                "lexicon_tree": composer.covered_tree(),
                "categories": len(taxonomy.CATEGORIES),
                "subs": len(taxonomy.SUB_INDEX),
                "total_nodes": taxonomy.total_nodes(),
            })
            return
        if p == "/api/loras":
            loras = moss_workflow.list_loras_with_triggers()
            self._json({"loras": loras})
            return
        if p == "/api/base_models":
            self._json({"models": moss_workflow.list_base_models()})
            return
        if p == "/api/char_styles":
            self._json({
                "tree": api_writer._CS.as_tree(),
                "categories": len(api_writer._CS.CHAR_TREE),
                "subs": len(api_writer._CS.SUB_INDEX),
            })
            return
        if p == "/api/detail_levels":
            self._json({"levels": api_writer._DT.as_list()})
            return
        if p == "/api/visual_styles":
            self._json({
                "tree": api_writer._STY.as_tree(),
                "categories": len(api_writer._STY.STYLE_TREE),
                "subs": len(api_writer._STY.SUB_INDEX),
            })
            return
        if p == "/api/progress":
            with PROGRESS_LOCK:
                snap = {k: dict(v) for k, v in PROGRESS.items()}
            self._json({"render": snap.get("render") or {}, "design": snap.get("design") or {}})
            return

        if p == "/api/aspects":
            self._json({
                "aspects": [{"label": a} for a, _ in moss_workflow.ASPECTS],
                "megapixels": [0.5, 1.0, 1.5, 2.0, 3.0, 4.0],
            })
            return
        if p == "/api/sampling_options":
            samplers, schedulers = [], []
            try:
                with urllib.request.urlopen(f"{config.BASE}/object_info/KSampler", timeout=8) as r:
                    info = json.loads(r.read().decode("utf-8"))
                inp = ((info.get("KSampler") or {}).get("input") or {})
                req = inp.get("required") or {}
                samplers = list((req.get("sampler_name") or [[]])[0] or [])
                schedulers = list((req.get("scheduler") or [[]])[0] or [])
            except Exception:
                pass
            if not samplers:
                samplers = ["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde",
                            "dpmpp_3m_sde", "ddim", "uni_pc", "heun"]
            if not schedulers:
                schedulers = ["simple", "normal", "karras", "exponential", "sgm_uniform",
                              "ddim_uniform", "beta"]
            self._json({"samplers": samplers, "schedulers": schedulers,
                        "default_steps": 34, "default_cfg": 3.0,
                        "default_sampler": "euler", "default_scheduler": "simple"})
            return
        if p == "/api/size_preview":
            q = parse_qs(u.query or "")
            try:
                mp = float((q.get("mp") or ["1"])[0])
            except ValueError:
                mp = 1.0
            aspect = (q.get("aspect") or ["2:3"])[0]
            w, h = moss_workflow.size_for_megapixels(mp, aspect)
            self._json({"width": w, "height": h, "megapixels": round(w * h / 1e6, 2)})
            return

        self._json({"error": "not found", "path": p}, 404)

    @guard
    def do_POST(self):
        p = urlparse(self.path).path
        try:
            body = self._body()
        except ValueError as e:
            self._json({"error": str(e)}, 400)
            return

        if p == "/api/ollama_unload":
            # Manual VRAM release for the local Ollama lane: no model name in
            # the body means "everything currently loaded" (/api/ps).
            try:
                res = api_writer.ollama_unload((body.get("model") or "").strip())
                self._json(res, 200 if res.get("ok") else 502)
            except Exception as e:
                self._json({"ok": False, "error": str(e), "unloaded": []}, 502)
            return

        if p in ("/api/render", "/api/render_async", "/api/render_moss"):
            # 排队里的写词任务可以继续跑、继续排队；但轮到出图开始的这一刻，
            # 本地 Ollama 模型必须从显存让位——8G 卡上 ComfyUI 出图与一个
            # 保温中的 Ollama 模型装不下。卸载失败不阻塞出图（ComfyUI 会
            # 以它自己的方式报显存不足）。
            try:
                api_writer.ollama_unload()
            except Exception:
                pass

        if p == "/api/draw":
            try:
                draws = composer.draw_many(
                    tier=body.get("tier", "normal"),
                    style=body.get("style", "random"),
                    count=int(body.get("count", 1)),
                    base_seed=self._opt_int(body.get("seed")),
                    view=body.get("view", "random"),
                    backdrop=body.get("backdrop", "studio"),
                )
            except Exception as e:
                self._json({"error": str(e)}, 400)
                return
            self._json({"draws": draws, "count": len(draws)})
            return

        if p == "/api/render":
            try:
                draws = composer.draw_many(
                    tier=body.get("tier", "normal"),
                    style=body.get("style", "random"),
                    count=int(body.get("count", 1)),
                    base_seed=self._opt_int(body.get("seed")),
                    view=body.get("view", "random"),
                    backdrop=body.get("backdrop", "studio"),
                )
                width = self._opt_int(body.get("width")) or 832
                height = self._opt_int(body.get("height")) or 1216
                steps = self._opt_int(body.get("steps")) or 4
            except Exception as e:
                self._json({"error": str(e)}, 400)
                return

            # A new render must start with a clean cancel flag, otherwise a
            # previous "中断" leaves CANCEL_FLAG set and this worker (which
            # checks it before ever reaching render_moss_blocking's own clear)
            # would mark itself cancelled and every subsequent LoRA render
            # would fail instantly. The no-LoRA branch clears at line ~686;
            # do it here too so both paths are covered.
            CANCEL_FLAG.clear()

            # The Krea2 path cannot load LoRAs. When the user has picked any, run
            # the same draws through the MOSS pipeline instead, which honours the
            # LoRA list, SeedVR2 and the chosen base model.
            if body.get("loras"):
                job = _job_new(len(draws), body.get("tier", "normal"),
                               body.get("style", "random"))

                def moss_worker(job=job, draws=list(draws), body=dict(body)):
                    for d in draws:
                        if CANCEL_FLAG.is_set():
                            with JOBS_LOCK:
                                job["status"] = "cancelled"
                            return
                        try:
                            payload = dict(body)
                            payload["prompt"] = d["prompt"]
                            payload["negative"] = d.get("negative", "")
                            payload["seed"] = d.get("seed")
                            payload.pop("count", None)
                            res = render_moss_blocking(payload)
                            item = dict(d)
                            item["image"] = res.get("image")
                            item["prompt_id"] = res.get("prompt_id")
                        except Exception as e:
                            traceback.print_exc()
                            item = dict(d)
                            item["image"] = None
                            item["error"] = str(e)[:400]
                        with JOBS_LOCK:
                            job["items"].append(item)
                            job["done"] = len(job["items"])
                    with JOBS_LOCK:
                        job["status"] = "done"

                threading.Thread(target=moss_worker, daemon=True).start()
                self._json({"job": _job_public(job)})
                return
            CANCEL_FLAG.clear()
            job = _job_new(len(draws), body.get("tier", "normal"), body.get("style", "random"))
            t = threading.Thread(
                target=_render_worker,
                args=(job, draws, width, height, steps, body.get("lora_triggers", "")),
                daemon=True,
            )
            t.start()
            self._json({"job": _job_public(job)})
            return

        if p == "/api/rerender":
            try:
                tier = body.get("tier", "normal")
                seed = self._opt_int(body.get("seed"))
                d = composer.draw_one(tier=tier, style=body.get("style", "random"),
                                      seed=seed, view=body.get("view", "random"),
                                      backdrop=body.get("backdrop", "studio"))
                width = self._opt_int(body.get("width")) or 832
                height = self._opt_int(body.get("height")) or 1216
                steps = self._opt_int(body.get("steps")) or 4
            except Exception as e:
                self._json({"error": str(e)}, 400)
                return
            try:
                with config.GPU_LANE_LOCK, RENDER_LOCK:
                    res = comfy.render(
                        prompt=d["prompt"], negative=d["negative"], seed=d["seed"],
                        tier=d["tier"], width=width, height=height, steps=steps,
                    )
                d["image"] = res.get("url")
                self._json({"draw": d})
            except Exception as e:
                traceback.print_exc()
                self._json({"error": str(e)}, 502)
            return

        if p == "/api/models":
            try:
                models = api_writer.list_models()
                self._json({"models": models})
            except Exception as e:
                self._json({"error": str(e)}, 502)
            return

        if p == "/api/system_prompts":
            prompts = moss_workflow.list_system_prompts()
            self._json({"prompts": [{"name": p["name"], "chars": len(p["content"])} for p in prompts]})
            return

        if p == "/api/loras":
            loras = moss_workflow.list_loras_with_triggers()
            self._json({"loras": loras})
            return

        if p == "/api/write_prompt":
            try:
                brief = body.get("brief", "")
                tier = body.get("tier", "normal")
                # `styles` (list) bounds the random range; `style` (single) kept
                # for compatibility.
                styles = body.get("styles")
                style = styles if isinstance(styles, list) and styles else body.get("style", "random")
                composition = body.get("composition", "full_body")
                model = body.get("model", "")
                lang = body.get("lang", "en")
                extra_name = body.get("system_prompt", "")
                extra = ""
                if extra_name:
                    for pr in moss_workflow.list_system_prompts():
                        if pr["name"] == extra_name:
                            extra = pr["content"]
                            break
                if not brief.strip():
                    self._json({"error": "请输入一句描述"}, 400)
                    return
                with PROGRESS_LOCK:
                    PROGRESS["design"] = {"phase": "designing", "percent": 5.0,
                                          "model": model or "", "chars": 0,
                                          "eta": 30, "step": 0, "steps": 0}
                result = api_writer.write_prompt(
                    brief=brief,
                    tier=tier,
                    style=style,
                    composition=composition,
                    extra_system=extra,
                    model=model,
                    lang=lang,
                    visual_style=body.get("visual_style", "none"),
                    with_action=bool(body.get("with_action")),
                    detail=body.get("detail", "normal"),
                    char_style=body.get("char_style", "none"),
                    enabled_blocks=body.get("enabled_blocks"),
                    think=_norm_think(body.get("think")),
                )
                with PROGRESS_LOCK:
                    PROGRESS["design"] = {"phase": "designed", "percent": 70.0,
                                          "model": result.get("model", ""),
                                          "chars": len(result.get("prompt", "")),
                                          "eta": 10}
                # The close-up companion comes out of the SAME model call: the
                # 大头提示词 module asks for a -XXX- segment at the end of the
                # prompt, and api_writer.split_headshot() cuts it apart. Keep
                # what the splitter found — clearing it here threw the
                # automatic result away and left only the manual button.
                result.setdefault("prompt_headshot", "")
                # A companion exists (or can still be produced) unless the
                # composition already IS the close-up.
                result["headshot_ready"] = (
                    bool(result["prompt_headshot"])
                    or api_writer.needs_headshot(composition)
                )
                with PROGRESS_LOCK:
                    PROGRESS["design"] = {"phase": "done", "percent": 100.0,
                                          "model": result.get("model", ""),
                                          "chars": len(result.get("prompt", "")),
                                          "eta": 0}
                # 无保温策略：写完词就卸载。请求体里 keep_alive=0 已经让
                # Ollama 生成完立即倒出显存；这里再后台兜底卸一次，确保
                # 写词返回后显存必空。后台线程不阻塞结果返回。
                threading.Thread(
                    target=lambda: _safe(lambda: api_writer.ollama_unload()),
                    daemon=True).start()
                result["vram_unloaded"] = {"ok": True, "unloaded": [],
                                           "note": "后台卸载中"}
                self._json({"result": result})
            except Exception as e:
                traceback.print_exc()
                self._json({"error": str(e)}, 502)
            return

        if p == "/api/save_design_method":
            tier = body.get("tier", "")
            text = body.get("text", "")
            fname = design.TIER_FILES.get(tier)
            if not fname:
                self._json({"error": f"未知档位：{tier}"}, 400)
                return
            if not isinstance(text, str) or not text.strip():
                self._json({"error": "内容不能为空"}, 400)
                return
            path = os.path.join(design.DESIGN_DIR, fname)
            try:
                # Keep one backup so a bad edit can be undone by hand.
                if os.path.isfile(path):
                    bak = path + ".bak"
                    try:
                        with open(path, encoding="utf-8") as src:
                            prev = src.read()
                        with open(bak, "w", encoding="utf-8") as dst:
                            dst.write(prev)
                    except OSError:
                        pass
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
            except OSError as e:
                self._json({"error": f"写入失败：{e}"}, 500)
                return
            api_writer.invalidate_method_cache()
            self._json({"ok": True, "tier": tier, "file": fname, "chars": len(text)})
            return
        if p == "/api/render_async":
            # Start the render in a worker and answer at once: a browser should
            # never hold a request open for the eight minutes a cold MOSS run
            # takes, and holding it is what made 出这张 look unresponsive.
            prompt = (body.get("prompt") or "").strip()
            if not prompt:
                self._json({"error": "prompt is empty"}, 400)
                return
            if state_busy_render():
                self._json({"error": "已有出图任务在进行"}, 429)
                return

            job_id = uuid.uuid4().hex[:12]
            with RENDER_JOBS_LOCK:
                RENDER_JOBS[job_id] = {"status": "running", "image": "",
                                       "error": "", "started": time.time(),
                                       "last_seen": time.time()}

            def work(jid=job_id, payload=dict(body)):
                try:
                    res = render_moss_blocking(payload)
                    with RENDER_JOBS_LOCK:
                        j = RENDER_JOBS.get(jid)   # may have been reaped as stale
                        if j is not None:
                            j.update(status="done", image=res.get("image", ""),
                                     steps=res.get("steps"), error="")
                except Exception as e:
                    traceback.print_exc()
                    with RENDER_JOBS_LOCK:
                        j = RENDER_JOBS.get(jid)
                        if j is not None:
                            j.update(status="error", error=str(e)[:300])
                finally:
                    # Guarantee a terminal state even if something above threw
                    # outside the try (e.g. an error while formatting the dict).
                    with RENDER_JOBS_LOCK:
                        j = RENDER_JOBS.get(jid)
                        if j is not None and j.get("status") == "running":
                            j.update(status="error", error="render ended without result")

            threading.Thread(target=work, daemon=True).start()
            self._json({"job": job_id})
            return

        if p == "/api/render_status":
            jid = (body.get("job") or "").strip()
            with RENDER_JOBS_LOCK:
                live = RENDER_JOBS.get(jid)
                if not live:
                    self._json({"error": "未知任务"}, 404)
                    return
                live["last_seen"] = time.time()   # browser still watching: keep alive
                j = dict(live)
                if j.get("status") in ("done", "error"):
                    RENDER_JOBS.pop(jid, None)   # read once, then forget
            self._json(j)
            return

        if p == "/api/api_request":
            # The exact system+user text this draw would send, plus the module
            # outline the UI lists as jump buttons.
            try:
                brief = body.get("brief", "")
                tier = body.get("tier", "normal")
                styles = body.get("styles")
                style = styles if isinstance(styles, list) and styles else body.get("style", "random")
                composition = body.get("composition", "full_body")
                lang = body.get("lang", "en")
                extra_name = body.get("system_prompt", "")
                extra = ""
                if extra_name:
                    for pr in moss_workflow.list_system_prompts():
                        if pr["name"] == extra_name:
                            extra = pr["content"]
                            break
                asm = api_writer.build_prompt(
                    brief=brief, tier=tier, style=style,
                    composition=composition, lang=lang,
                    visual_style=body.get("visual_style", "none"),
                    with_action=bool(body.get("with_action")),
                    detail=body.get("detail", "normal"),
                    extra_system=extra,
                    char_style=body.get("char_style", "none"),
                    enabled_blocks=body.get("enabled_blocks"),
                )
                system, user = asm.system, asm.user
                style_key, _b, _i = api_writer.resolve_style(style)
                self._json({
                    "system": system,
                    "user": user,
                    "blocks": asm.outline(),
                    "style_key": style_key,
                    "style_zh": api_writer.style_label(style),
                    "tier": tier,
                    "detail_zh": api_writer._DT.label(body.get("detail", "normal")),
                    "char_style_zh": api_writer.char_label(body.get("char_style", "none")),
                    "visual_style_zh": api_writer.style_label(
                        body.get("visual_style", "none")),
                    "needs_headshot": api_writer.needs_headshot(composition),
                    "chars": len(system) + len(user),
                })
            except Exception as e:
                traceback.print_exc()
                self._json({"error": str(e)}, 502)
            return
        if p == "/api/rewrite_composition":
            try:
                r = api_writer.rewrite_composition(
                    prompt=body.get("prompt", ""),
                    target=body.get("target", "full_body"),
                    source=body.get("source", ""),
                )
                self._json(r)
            except Exception as e:
                self._json({"error": str(e)}, 400)
            return

        if p == "/api/delete_outputs":
            # Card 删除按钮: remove the rendered image files that belong to
            # the deleted card. basename-only + realpath containment so a
            # crafted name cannot reach outside the outputs directory.
            names = body.get("names") or []
            base = os.path.realpath(OUT)
            removed, errors = [], []
            for n in names[:40]:
                fn = os.path.basename(str(n))
                fp = os.path.realpath(os.path.join(OUT, fn))
                if not fn or not fp.startswith(base + os.sep) or not os.path.isfile(fp):
                    errors.append(fn)
                    continue
                try:
                    os.remove(fp)
                    removed.append(fn)
                except OSError as e:
                    errors.append(f"{fn}: {e}")
            self._json({"ok": True, "removed": removed, "errors": errors})
            return

        if p == "/api/cancel":
            # Clear the queue and interrupt the runner; the flag stops a render
            # that has not submitted yet. The write ladder gets the same
            # signal: without it a cancelled comfyui write would just crawl
            # into the next model and re-occupy the queue.
            kind = body.get("kind", "render")
            killed = _cancel_comfy_work()
            api_writer.cancel_write()
            with JOBS_LOCK:
                for job in JOBS.values():
                    if job["status"] == "running":
                        job["status"] = "cancelled"
            self._json({"ok": True, "kind": kind, "comfy": killed})
            return

        if p == "/api/heartbeat":
            # The WebUI app window pings this while it is open. Only the app
            # window (or any tab of this UI) sends it; the daemon in main()
            # exits the server once pings stop for HEARTBEAT_TIMEOUT seconds.
            with HEARTBEAT_LOCK:
                HEARTBEAT["t"] = time.time()
                HEARTBEAT["seen"] = True
            self._json({"ok": True})
            return

        if p == "/api/quit":
            # Answer first, then shut down from a separate thread — calling
            # shutdown() inline would deadlock the request that is still being
            # served. Give the browser a moment to receive the 200 before the
            # loop stops, then hard-exit so daemon render threads can't keep
            # the interpreter alive.
            self._json({"ok": True})
            def _quit():
                time.sleep(0.6)
                srv = SERVER
                if srv:
                    try:
                        srv.shutdown()
                    except Exception:
                        pass
                os._exit(0)
            threading.Thread(target=_quit, daemon=True).start()
            return

        if p == "/api/render_moss":
            try:
                res = render_moss_blocking(body)
                self._json(res)
            except ValueError as e:
                self._json({"error": str(e)}, 400)
            except Exception as e:
                traceback.print_exc()
                self._json({"error": str(e)}, 502)
            return
        self._json({"error": "not found", "path": p}, 404)

    # ---------------------------------------------------------------- handlers
    def _health(self):
        models = config.discover()
        comfy_ok = False
        comfy_err = None
        try:
            import urllib.request
            with urllib.request.urlopen(config.BASE + "/system_stats", timeout=5) as r:
                r.read(16)
            comfy_ok = True
        except Exception as e:
            comfy_err = str(e)
        self._json({
            "ok": True,
            "comfyui": {"online": comfy_ok, "base": config.BASE, "error": comfy_err},
            "models": {
                "unet_by_tier": {k: os.path.basename(v) for k, v in models["unet_by_tier"].items()},
                "clip": os.path.basename(models.get("clip") or ""),
                "vae": models.get("vae"),
                "lora_4step": os.path.basename(models.get("lora_4step") or ""),
            },
            "stats": {"total_combinations": composer.matrix_stats()["total"]},
        })

    def _one_off(self, query: str):
        q = parse_qs(query)
        tier = (q.get("tier") or ["normal"])[0]
        style = (q.get("style") or ["random"])[0]
        seed = (q.get("seed") or [""])[0]
        try:
            d = composer.draw_one(tier=tier, style=style,
                                  seed=int(seed) if seed else None,
                                  view=(q.get("view") or ["random"])[0],
                                  backdrop=(q.get("backdrop") or ["studio"])[0])
            with config.GPU_LANE_LOCK, RENDER_LOCK:
                res = comfy.render(prompt=d["prompt"], negative=d["negative"],
                                   seed=d["seed"], tier=d["tier"])
            d["image"] = res.get("url")
            self._json({"draw": d})
        except Exception as e:
            traceback.print_exc()
            self._json({"error": str(e)}, 502)


def _heartbeat_watch():
    """Exit the server once the WebUI window stops sending heartbeats.

    Only arms after the first ping arrives, so starting the server before the
    app window is opened does not kill it during that gap. A refresh pauses
    pings for ~1s, far below the 12s timeout, so it is never mistaken for a
    closed window.
    """
    while True:
        time.sleep(2.0)
        with HEARTBEAT_LOCK:
            seen = HEARTBEAT["seen"]
            last = HEARTBEAT["t"]
        if not seen:
            continue
        if time.time() - last < HEARTBEAT_TIMEOUT:
            continue
        print("[heartbeat] 窗口心跳停止 %.0fs，关闭后台服务" % HEARTBEAT_TIMEOUT)
        srv = SERVER
        if srv:
            try:
                srv.shutdown()
            except Exception:
                pass
        os._exit(0)


def _thread_excepthook(args):
    """后台 worker 线程里漏出的异常也落盘（不会冒泡到 HTTP guard）。"""
    applog.log_exc("后台线程崩溃: %s" % getattr(args.thread, "name", "?"), args.exc_value)


def main():
    global SERVER
    # 全局异常兜底：HTTP 路由走 guard 装饰器，线程走 excepthook，
    # 从此 pythonw 无控制台启动也不会有"静默失败查不到"的情况。
    threading.excepthook = _thread_excepthook
    applog.info("server starting")
    os.makedirs(OUT, exist_ok=True)
    # 后台预热 comfyui 模型缓存（不阻塞启动，让磁盘镜像跟上最新模型列表）
    api_writer.prewarm_comfyui_models()
    models = config.discover()
    print("=" * 64)
    print("dress-gacha  ->  http://%s:%d" % (HOST, PORT))
    print("unet normal :", os.path.basename(models["unet_by_tier"].get("normal") or "MISSING"))
    print("unet nude   :", os.path.basename(models["unet_by_tier"].get("nude") or "MISSING"))
    print("clip        :", os.path.basename(models.get("clip") or "MISSING"))
    print("vae         :", models.get("vae") or "MISSING")
    print("lora 4step  :", os.path.basename(models.get("lora_4step") or "MISSING"))
    print("combinations:", composer.matrix_stats()["total"])
    print("=" * 64)

    # A render thread can outlive the request that started it. Without
    # daemon_threads the interpreter waits on it at exit, and a client that
    # reconnects while workers are still draining can stall behind them.
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    SERVER = srv
    # Close the backend when the WebUI app window is closed (heartbeat stops).
    threading.Thread(target=_heartbeat_watch, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
