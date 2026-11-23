# -*- coding: utf-8 -*-
"""原生独立窗口启动器：pywebview + 系统 WebView2（不是 Edge 浏览器外壳）。

- 加载本地 WebUI：http://127.0.0.1:8770
- 用固定的 storage_path 作为 WebView2 UserDataFolder，localStorage 持久保留
- 首次启动把旧 Edge --app 模式下 127.0.0.1:8770 站点的 localStorage 迁过来，
  这样卡片/设置不会因为在浏览器和原生窗口之间切换而丢失。

自测：设环境变量 DRESS_GACHA_WINDOW_TEST=1，窗口 6 秒后自动关闭并打印日志。
"""
import os
import sys
import json
import time
import shutil
import tempfile
import threading
import urllib.request

APP = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("DRESS_GACHA_URL", "http://127.0.0.1:8770")
PROFILE = os.path.join(APP, "data", "webview-profile")
MARKER = os.path.join(PROFILE, ".localstorage_migrated")
ORIGIN = b"127.0.0.1:8770"


def _edge_localstorage_dir():
    local = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local, "Microsoft", "Edge", "User Data", "Default",
                        "Local Storage", "leveldb")


def migrate_localstorage():
    """一次性把旧 Edge profile 里本站的 localStorage leveldb 迁到 WebView2。"""
    if os.path.exists(MARKER):
        return "already"
    src = _edge_localstorage_dir()
    if not os.path.isdir(src):
        return "no-edge-profile"
    # 确认源里确实存过本站数据，避免把无关 profile 整包拷过来
    found = False
    try:
        for fn in os.listdir(src):
            fp = os.path.join(src, fn)
            if not os.path.isfile(fp):
                continue
            with open(fp, "rb") as fh:
                if ORIGIN in fh.read():
                    found = True
                    break
    except Exception:
        return "read-failed"
    if not found:
        return "no-site-data"

    # WebView2 会在 storage_path 下再建一层 EBWebView/，localStorage 的真正在此。
    dst_parent = os.path.join(PROFILE, "EBWebView", "Default", "Local Storage")
    dst = os.path.join(dst_parent, "leveldb")
    try:
        os.makedirs(dst_parent, exist_ok=True)
        tmp = tempfile.mkdtemp(prefix="ls-", dir=dst_parent)
        for fn in os.listdir(src):
            fp = os.path.join(src, fn)
            if os.path.isfile(fp):
                shutil.copy2(fp, os.path.join(tmp, fn))
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.rename(tmp, dst)
        with open(MARKER, "w", encoding="ascii") as fh:
            fh.write("1")
        return "migrated"
    except Exception as exc:
        sys.stderr.write("[migrate] localStorage 迁移跳过: %r\n" % (exc,))
        return "failed:%s" % exc


_quitting = False          # 防止 X 关闭与退出按钮重复触发退出序列
_quitting_lock = threading.Lock()


def do_quit():
    """统一的退出序列：先关后端服务，再销毁所有原生窗口。

    "退出"按钮和窗口右上角 X 都走这里，保证行为完全一致：不会留下孤儿
    server 进程，也不会留下一个显示"程序已退出"的死页面。
    """
    global _quitting
    with _quitting_lock:
        if _quitting:
            return
        _quitting = True

    def _do():
        try:
            req = urllib.request.Request(
                URL.rstrip("/") + "/api/quit",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=2).read()
        except Exception:
            pass
        # Give the quit request a beat to land before tearing down WebView2.
        time.sleep(0.25)
        for w in list(webview_mod.windows):
            try:
                w.destroy()
            except Exception:
                pass

    threading.Thread(target=_do, daemon=True).start()


class Api:
    """Exposed to the page as window.pywebview.api — used by the 退出 button."""

    def quit(self):
        """Kill the backend, then close this native window."""
        do_quit()
        return True


def main():
    global webview_mod
    result = migrate_localstorage()
    print("[desktop] localStorage migration:", result, flush=True)

    # 启动前依赖自检：缺 pywebview 时给清晰指引，而不是静默失败/留下孤儿进程。
    # （server.py 只用标准库，不在此检查；窗口启动器是唯一需要第三方包的地方。）
    try:
        import webview as webview_mod
    except ImportError as exc:
        msg = (
            "缺少原生窗口依赖 pywebview，窗口无法启动。\n"
            "安装方式（隔离环境）：\n"
            "  \"%s\" -m pip install -r \"%s\"\n"
            "原始错误：%s\n" % (sys.executable, os.path.join(APP, "requirements.txt"), exc)
        )
        # 写日志 + 弹控制台提示，即使从 pythonw 无控制台启动也有据可查
        try:
            with open(os.path.join(APP, "data", "desktop_window.err"), "a", encoding="utf-8") as fh:
                fh.write(msg + "\n")
        except Exception:
            pass
        sys.stderr.write(msg)
        raise
    webview = webview_mod

    # REMOTE_DEBUGGING_PORT 在 create_window 创建 browser 时读取，必须提前设。
    if os.environ.get("DRESS_GACHA_WINDOW_TEST"):
        webview.settings["REMOTE_DEBUGGING_PORT"] = 9223

    icon = os.path.join(APP, "web", "app.ico")
    kwargs = {}
    if os.path.isfile(icon):
        kwargs["icon"] = icon

    win = webview.create_window(
        "装扮抽卡",
        URL,
        width=1280,
        height=900,
        min_size=(960, 640),
        text_select=True,   # 提示词要能选中复制
        js_api=Api(),       # 让页面里的"退出"按钮能真正关掉这个窗口
        **kwargs,
    )

    def _on_closing():
        """窗口右上角 X：取消默认关闭，改走和"退出"按钮一样的退出序列。

        pywebview 的 closing 是可取消事件：handler 返回 False 会阻止窗口关闭。
        我们借此拦下 X，调用 do_quit()（关后端 + destroy 窗口）。do_quit() 里
        destroy 会二次触发本 handler，此时 _quitting 已置位，返回 None 不再取消，
        让窗口真正关闭 —— 因此不会递归、也不会留下孤儿进程。
        """
        if _quitting:
            return None      # 退出序列已在进行中（destroy 引发），放行关闭
        do_quit()
        return False         # 取消这次 X 关闭；由 do_quit 的 destroy 统一收尾

    win.events.closing += _on_closing

    if os.environ.get("DRESS_GACHA_WINDOW_TEST") and not os.environ.get("DRESS_GACHA_WINDOW_HOLD"):
        import threading
        import time

        def _auto_close():
            time.sleep(6)
            print("[desktop] self-test: closing window", flush=True)
            try:
                win.destroy()
            except Exception:
                pass

        threading.Thread(target=_auto_close, daemon=True).start()

    # private_mode=False 是关键：默认 True 会让 WebView2 在退出时清空 UserDataFolder，
    # 那样迁移过来的 localStorage（卡片/设置）会全部丢失。
    webview.start(
        storage_path=PROFILE,
        private_mode=False,
        debug=bool(os.environ.get("DRESS_GACHA_WINDOW_TEST")),
    )


if __name__ == "__main__":
    main()
