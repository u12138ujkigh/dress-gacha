# dress-gacha 运维速查

面向"改项目 / 排障 / 换环境"时看。历史变更流水仍在 `README.md`。

## 启动

双击桌面 `装扮抽卡` 快捷方式（→ `启动.vbs` → `启动.ps1` → 无黑框原生窗口 + 后端）。
手动：`启动.bat` / `启动.vbs`。关闭：界面内「退出」或窗口右上角 X（两者等价，都会关后端）。

## 依赖

- 后端 `server.py` + `engine/`：仅 Python 标准库，系统 Python 3.13 直接跑。
- 原生窗口 `desktop_window.py`：pywebview（隔离 venv）。
  装依赖：`"C:\Users\ximu\.workbuddy\binaries\python\envs\default\Scripts\python.exe" -m pip install -r requirements.txt`
  缺依赖时窗口不静默失败，会写 `data/desktop_window.err` 并弹提示。

## 可编辑规则（改完即生效，无需改代码 / 重启）

- `rules/head_prompt.txt` — 大头提示词规则（锁骨以上 + 完整发型发饰 + -XXX- 拆分）。
  直接编辑此文件，下次写词自动热加载（按文件修改时间检测，不重启）。
  文件缺失或损坏时自动回退到 `engine/api_writer.py` 里的内置常量。
- `design_methods/*.md` — 各档位方法规则（已有热加载机制，走 `/api/design_method`）。

## 日志（排障先看这里）

- `data/app.log` — 统一应用日志：HTTP 请求异常、后台线程崩溃、写词网关失败、规则热加载。
  2 MB 自动轮转到 `app.log.1`。从 pythonw 无控制台启动时，这是唯一的异常线索。
- `data/launch.log` — 启动链日志（git 初始化 / 环境变量去重 / server / 窗口各步骤）。
- `data/server.log` — server.py stdout banner 与请求行。

## 测试

统一入口：`python tests/run_tests.py`（标准库 unittest，纯逻辑，无需浏览器/网络）。
覆盖：大头段拆分、保存路径、组合矩阵、规则热加载。
历史遗留：`tests/_verify_*.py` 是早期依赖 CDP 远程调试端口的 E2E 脚本，该端口已废弃，不再作为常规回归；保留仅作参考。

## 版本控制

项目已是 git 仓库。baseline 提交：`52c31f9`（清理与优化前快照）。
`.gitignore` 排除 `data/`（含卡片 localStorage、模型缓存、图片）、旧 profile、调试产物。
改坏了可 `git diff` / `git checkout` 回滚源码；**data/ 不被跟踪，删除前务必手动备份**。

## 关键路径配置

- ComfyUI 地址 / 输出目录 / GPU 串行锁 / 清缓存：`engine/config.py`
- 输出路径单一真源：`config.WEBUI_OUT` → `E:\Comfy-Desktop\ComfyUI-Shared\output\1图片\正反面和大头`
- 模型秒显缓存：`data/comfyui_models.json`（勿删）
- WebView2 用户数据（卡片/设置）：`data/webview-profile`（勿删）

## 环境坑（已修复，勿回退）

- PowerShell 7 的 `Start-Process` 遇大小写重复环境变量（http_proxy/HTTP_PROXY）会抛
  `ArgumentException` 静默失败 —— `启动.ps1` 开头已做 env 去重。
- 窗口关闭与退出按钮统一走 `desktop_window.py::do_quit()`，带防重入，不留孤儿进程。
