# -*- coding: utf-8 -*-
"""Verify Chinese tab labels and that the headshot is a program-driven second call."""
from __future__ import annotations

import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cdp import attach

c = attach()
c.call("Runtime.enable")
c.call("Page.enable")
c.call("Page.reload", {"ignoreCache": True})
time.sleep(9)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


print("=== 1. 标签已中文化 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(3)
tabs = c.eval("Array.from(document.querySelectorAll('.reqtab')).map(b=>b.textContent.trim())")
print("   实际标签:", tabs)
check("有四个 tab", len(tabs) == 4, str(len(tabs)))
check("无 user 英文", not any("user" in t.lower() for t in tabs), str(tabs))
check("无 system 英文", not any("system" in t.lower() for t in tabs), str(tabs))
check("含用户消息", any("用户消息" in t for t in tabs), str(tabs))
check("含系统提示词", any("系统提示词" in t for t in tabs), str(tabs))

print("\n=== 2. 请求文本里不再有字段要求 ===")
d = c.eval("""(async()=>{
  const r = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'full_body', lang:'zh', visual_style:[], with_action:false,
      system_prompt:''})});
  return JSON.stringify(await r.json());
})()""", await_promise=True)
import json as _j
probe = _j.loads(d)
u = probe["user"]
check("无 rewritten_prompt_headshot 字样", "rewritten_prompt_headshot" not in u)
check("无 rewritten_prompt_headshot_headshot 字样", "rewritten_prompt_headshot_headshot" not in u)
check("无「额外输出一个字段」", "额外输出一个字段" not in u)
check("user 长度合理（含维度+详细度+画风）", len(u) < 5200, f"{len(u)} 字")

print("\n=== 3. 大头是程序判定 ===")
check("全身照 needs_headshot=True", probe["needs_headshot"] is True)
d2 = c.eval("""(async()=>{
  const r = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'headshot', lang:'zh', visual_style:[], with_action:false,
      system_prompt:''})});
  return JSON.stringify(await r.json());
})()""", await_promise=True)
probe2 = _j.loads(d2)
check("大头照 needs_headshot=False", probe2["needs_headshot"] is False)
check("大头照也不含字段要求", "rewritten_prompt_headshot" not in probe2["user"])

print("\n=== 4. 预览不再有大头 tab ===")
check("请求区有 4 个 tab", c.eval("document.querySelectorAll('.reqtab').length") == 4)
check("无 data-part=headshot", c.eval("!document.querySelector('.reqtab[data-part=headshot]')"))
# The close-up is now a MANUAL step: the note must say how to get one.
_notes = c.eval("document.querySelector('#apiNotes').textContent") or ""
# The close-up is now split out of the SAME call: the note says the model
# returns a -XXX- segment that the tool cuts apart.
check("说明里写明自动拆分", ("-XXX-" in _notes) or ("自动拆分" in _notes) or ("手动提取" in _notes), _notes[:70])

print("\n=== 5. 切大头照构图时说明变化 ===")
c.eval("document.querySelector('#apiComposition').value='headshot';"
       "document.querySelector('#apiComposition').dispatchEvent(new Event('change'))")
time.sleep(3)
notes = c.eval("document.querySelector('#apiNotes').textContent") or ""
# The wording is "不另拆分" now that the close-up comes out of the same call.
check("大头照时说明不另拆分", ("不另拆分" in notes) or ("不另生成" in notes), notes[-40:])
c.eval("document.querySelector('#apiComposition').value='full_body';"
       "document.querySelector('#apiComposition').dispatchEvent(new Event('change'))")
time.sleep(3)

print("\n=== 6. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
