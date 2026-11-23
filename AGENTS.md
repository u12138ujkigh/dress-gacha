# AGENTS.md — 给 AI Agent 的项目操作指南

> 建议给 agent 安装：把本文件放到项目根目录，Claude Code / Codex / WorkBuddy 等
> agent 会自动读取它，从而了解这个项目怎么跑、怎么改、有哪些坑。

## 这个项目是什么

**装扮抽卡 · dress-gacha**：一个独立的本地 WebUI，用于「角色服装/造型提示词」抽卡。
四档强度（正常/擦边/裸露/色情）× 18 个品类随机组合，可以只出提示词，也可以联动
本机 ComfyUI 直接出图。它还有大头照/构图版两套独立结果与独立出图参数。

技术栈：后端 Python 标准库（零第三方依赖）+ 原生 JS 前端 + pywebview 独立窗口。
源码约 1.5 万行，主要文件见下方「代码地图」。

## 先读这些

- **README.md** — 功能与历史变更流水账（很长，按需搜索）
- **OPS.md** — 运维速查：启动、依赖、可编辑规则、日志、关键路径（推荐先读）

## 怎么启动 / 关闭

- 启动：双击 `启动.vbs`（无黑框，最稳）或 `启动.bat`；等价于
  `wscript 启动.vbs → powershell -File 启动.ps1 → server.py + desktop_window.py`
- 服务地址：`http://127.0.0.1:8770`
- 关闭：界面内「退出」按钮，或窗口右上角 X（两者**等价**，都会关后端 + 关窗口）
- 手动起后端：`py -3.13 server.py`
- 跑测试：`python tests/run_tests.py`（纯逻辑，无需浏览器/网络）

## 代码地图（改哪里）

| 想改什么 | 去哪里 |
|---|---|
| HTTP 路由 / 任务队列 / 出图调度 | `server.py`（单文件，40+ 路由，`@guard` 兜底异常） |
| 大头提示词规则 | **`rules/head_prompt.txt`**（直接编辑，热加载，无需重启） |
| 其它档位规则 | `design_methods/*.md`（已有热加载） |
| 词库 / 品类 / 组合矩阵 | `engine/lexicon.py`、`engine/taxonomy.py`、`engine/composer.py` |
| 写词网关 / 模型探测 / 规则拼装 | `engine/api_writer.py`（最大模块） |
| ComfyUI 普通出图桥 | `engine/comfy.py` |
| Moss 工作流 / LoRA 触发词 / 保存路径 | `engine/moss_workflow.py` |
| 全局配置与路径 / GPU 串行锁 / 清缓存 | `engine/config.py` |
| 统一日志 | `engine/applog.py` → `data/app.log` |
| 前端状态 / 队列 / 卡片 / 计时 | `web/app.js` |
| 前端结构 / 样式 | `web/index.html`、`web/style.css` |
| 原生窗口 / 退出逻辑 | `desktop_window.py` |

## 核心 API（本地 HTTP，GET 或 POST JSON）

| 端点 | 作用 |
|---|---|
| `/api/health` | ComfyUI / 模型 / 词库状态 |
| `/api/models` | 模型列表（comfyui 秒显，其它后台探测补齐） |
| `/api/draw` | 只抽提示词（body: tier/style/count/view/backdrop） |
| `/api/write_prompt` | 写一条提示词（body: brief/tier/styles/composition/model/...） |
| `/api/render_async` + `/api/render_status` | 异步出图 + 轮询（推荐路径） |
| `/api/render_moss` | Moss 工作流出图 |
| `/api/progress` | 当前任务的阶段/进度/eta |
| `/api/loras`、`/api/base_models`、`/api/styles` | 出图参数选项 |
| `/api/heartbeat` | 窗口保活（停止 12s 后端自动退出） |
| `/api/quit` | 关后端（退出按钮/X 会调它） |

完整路由见 `server.py` 的 `do_GET`/`do_POST`。

## 关键约束（务必遵守，踩过的坑）

1. **`data/` 目录绝不能删**：里面是卡片 localStorage（`webview-profile/`）、模型秒显缓存
   (`comfyui_models.json`)、生成的图片。它被 gitignore，删了无法从版本库恢复。
2. **提示词规则内容不要擅自改**：尤其 NSFW 档位（`design_methods/03`、`04`）和大头规则。
   用户明确要求规则只在被指示时调整。
3. **大头版 / 构图版是两套独立结果**：图存 `d.images.{main,head}`，耗时存
   `d.render_secs_map.{main,head}`。改卡片逻辑时两版都要照顾到。
4. **写词与出图抢 GPU**：8G 显存，写词与出图通过 `config.GPU_LANE_LOCK` 串行；
   出图前会清缓存、卸载 Ollama。不要破坏这个串行。
5. **PowerShell 7 环境变量大小写冲突**：`启动.ps1` 开头已对 `http_proxy/HTTP_PROXY`
   等做去重。删掉它会导致「打不开」（Start-Process 抛 ArgumentException 静默失败）。
6. **窗口退出统一走 `do_quit()`**：`desktop_window.py` 里退出按钮和窗口 X 共用，带防重入。
7. **出图组不可折叠**：`web/app.js` 里出图区承载「常规/大头」切换，折叠 key 曾用标题文本
   被污染，已改稳定 key。不要恢复成可折叠。

## 排障入口

- 启动失败 → `data/launch.log`（git 初始化 / env 去重 / server / 窗口各步骤）
- 请求/线程异常 → `data/app.log`（统一日志，含完整 traceback）
- server 输出 → `data/server.log`
- 窗口依赖缺失 → `data/desktop_window.err`
- 规则没生效 → 确认改的是 `rules/head_prompt.txt`（热加载按 mtime，改完下次写词生效）

## 环境与版本

- 后端 Python 3.13（系统 `py -3.13`），只依赖标准库
- 原生窗口用隔离 venv：`C:\Users\ximu\.workbuddy\binaries\python\envs\default`，
  依赖 pywebview 6.2（见 `requirements.txt`）
- 本机 ComfyUI Desktop：`E:\Comfy-Desktop\ComfyUI-Installs\ComfyUI`
- 输出目录：`E:\Comfy-Desktop\ComfyUI-Shared\output\1图片\正反面和大头`
- 这些路径在 `engine/config.py` 均有环境变量覆盖，**换环境改那里或设环境变量**。

## 版本控制

git 仓库，两个 commit：`52c31f9`（baseline）+ `9cc48ab`（优化）。改坏了可 `git diff` /
`git checkout` 回滚源码（data/ 不被跟踪，注意备份）。
