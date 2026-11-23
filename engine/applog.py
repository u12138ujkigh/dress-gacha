# -*- coding: utf-8 -*-
"""统一应用日志：零依赖、线程安全，写 data/app.log。

目的：把过去那些被 `except: pass` 静默吞掉的异常留下痕迹。排查时看这个文件，
而不是靠临时注入 Trace。日志写到项目 data/ 下，已被 .gitignore 排除。
"""
from __future__ import annotations

import os
import threading
import time
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG = os.path.join(_ROOT, "data", "app.log")
_LOCK = threading.Lock()
_MAX_BYTES = 2 * 1024 * 1024   # 2 MB 后轮转，避免长期运行撑爆


def _rotate_if_needed():
    try:
        if os.path.exists(_LOG) and os.path.getsize(_LOG) > _MAX_BYTES:
            os.replace(_LOG, _LOG + ".1")
    except Exception:
        pass


def write(level: str, msg: str, exc: BaseException | None = None):
    """写一条日志；exc 非空时附带完整 traceback。"""
    line = "%s [%-5s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), level, msg)
    if exc is not None:
        line += "\n" + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        with _LOCK:
            os.makedirs(os.path.dirname(_LOG), exist_ok=True)
            _rotate_if_needed()
            with open(_LOG, "a", encoding="utf-8") as fh:
                fh.write(line.rstrip() + "\n")
    except Exception:
        pass   # 日志本身失败绝不能影响业务


def info(msg: str):
    write("INFO", msg)


def warn(msg: str, exc: BaseException | None = None):
    write("WARN", msg, exc)


def error(msg: str, exc: BaseException | None = None):
    write("ERROR", msg, exc)


def log_exc(where: str, exc: BaseException):
    """在 `except Exception as e:` 里调用：log_exc('写词网关', e)。"""
    write("ERROR", where, exc)
