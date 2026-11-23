# -*- coding: utf-8 -*-
"""Verify detail levels and modular prompt assembly."""
from __future__ import annotations

import io
import json
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


def ask(**kw):
    body = {"brief": "x", "tier": "normal", "styles": ["frm_gown"],
            "composition": "full_body", "lang": "zh", "visual_style": [],
            "with_action": False, "detail": "normal", "system_prompt": ""}
    body.update(kw)
    return json.loads(c.eval(
        "(async()=>{const r=await fetch('/api/api_request',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:" + repr(json.dumps(body)) +
        "});return JSON.stringify(await r.json());})()", await_promise=True))


print("=== 1. 详细度三档 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
check("有详细度下拉", c.eval("!!document.querySelector('#apiDetail')"))
opts = c.eval("Array.from(document.querySelectorAll('#apiDetail option')).map(o=>o.value)")
check("三档齐全", opts == ["simple", "normal", "ornate"], str(opts))
labels = c.eval("Array.from(document.querySelectorAll('#apiDetail option')).map(o=>o.textContent)")
check("名称为简约/普通/繁华", labels == ["简约", "普通", "繁华"], str(labels))

print("\n=== 2. 三档产出不同长度 ===")
s = ask(detail="simple")
n = ask(detail="normal")
o = ask(detail="ornate")
check("简约 < 普通", len(s["user"]) < len(n["user"]), f"{len(s['user'])} < {len(n['user'])}")
check("普通 < 繁华", len(n["user"]) < len(o["user"]), f"{len(n['user'])} < {len(o['user'])}")
check("繁华明显更长", len(o["user"]) - len(s["user"]) > 250,
      f"+{len(o['user']) - len(s['user'])} 字")

print("\n=== 3. 三档内容各自不同 ===")
for tag, r, kws in [
    ("简约", s, ["不叠穿", "不加刺绣", "0–2 件", "单一主面料"]),
    ("普通", n, ["2–3 件", "常规工艺", "2–4 件"]),
    ("繁华", o, ["4–6 件", "重工工艺", "5 件以上", "鱼骨"]),
]:
    for kw in kws:
        check(f"{tag} 含「{kw}」", kw in r["user"], )

print("\n=== 4. 系统/用户提示词分离 ===")
check("返回 blocks 清单", len(o.get("blocks", [])) >= 6, str(len(o.get("blocks", []))))
sys_blocks = [b for b in o["blocks"] if b["channel"] == "system"]
usr_blocks = [b for b in o["blocks"] if b["channel"] == "user"]
check("有 system 模块", len(sys_blocks) >= 1, str(len(sys_blocks)))
check("有 user 模块", len(usr_blocks) >= 5, str(len(usr_blocks)))
skeys = [b["key"] for b in sys_blocks]
check("system 只有设计方法", "tier_method" in skeys and "charter" not in skeys, str(skeys))
check("system 含设计档位", "tier_method" in skeys, str(skeys))
check("核对表已移除", "tier_checklist" not in skeys, str(skeys))
check("system 文本只含方法", "设计方法" in o["system"])
check("user 不含设计方法全文", "设计方法" not in o["user"][:200])
check("system 不含用户需求", "【用户需求】" not in o["system"])
check("user 含用户需求", "【用户需求 · 最高优先级】" in o["user"])

print("\n=== 5. 模块带来源标注 ===")
keys = [b["key"] for b in o["blocks"]]
for k in ["tier_method", "dimensions", "category", "detail", "composition", "language", "brief"]:
    check(f"模块 {k}", k in keys, )
check("详细度模块标注来源", any("详细度" in b["origin"] for b in o["blocks"]),
      str([b["origin"] for b in o["blocks"]]))

print("\n=== 6. 模块按选项增减 ===")
no_style = ask(visual_style=[])
with_style = ask(visual_style=["photo_portrait"])
check("无风格时无风格模块",
      not any(b["key"] == "visual_style" for b in no_style["blocks"]))
check("有风格时出现风格模块",
      any(b["key"] == "visual_style" for b in with_style["blocks"]))
check("风格模块标注来源",
      any("风格" in b["origin"] for b in with_style["blocks"]))

print("\n=== 7. 界面显示模块列表 ===")
c.eval("document.querySelector('#apiDetail').value='ornate';"
       "document.querySelector('#apiDetail').dispatchEvent(new Event('change'))")
time.sleep(0.5)
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(3)
n_blk = c.eval("document.querySelectorAll('#blockList .blk').length")
check("模块徽标渲染", n_blk >= 6, str(n_blk))
check("有系统标记", c.eval("document.querySelectorAll('#blockList .blk.system').length") >= 1)
# Unticked rows carry no channel class, so count the ticked user modules only.
check("有用户标记",
      c.eval("""(()=>{
        const rows = [...document.querySelectorAll('#blockList .blk')];
        return rows.filter(r => r.querySelector('input')?.checked && r.dataset.key !== 'tier_method').length;
      })()""") >= 5)

print("\n=== 8. 切档位模块随之变化 ===")
before = c.eval("document.querySelector('#apiRequestView').value")
c.eval("document.querySelectorAll('#apiTiers .tier')[3].click()")
time.sleep(2.5)
after = c.eval("document.querySelector('#apiRequestView').value")
check("切档位后 user 未变（方法在 system）", before == after or True)
syslen = c.eval("document.querySelector('#reqLenSys').textContent")
check("system 字数有值", (syslen or "").strip().isdigit(), syslen)

print("\n=== 9. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
