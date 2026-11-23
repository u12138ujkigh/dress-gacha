# -*- coding: utf-8 -*-
"""Verify the four-family style taxonomy, the action option, and style-driven design."""
from __future__ import annotations

import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cdp import attach

c = attach()
c.call("Runtime.enable")
c.call("Emulation.setDeviceMetricsOverride",
       {"width": 1680, "height": 950, "deviceScaleFactor": 1, "mobile": False})
c.call("Page.enable")
c.call("Page.reload", {"ignoreCache": True})
time.sleep(9)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def ask(**kw):
    import json
    body = {"brief": "x", "tier": "normal", "styles": ["formal"],
            "composition": "full_body", "lang": "zh",
            "visual_style": [], "with_action": False, "system_prompt": ""}
    body.update(kw)
    return json.loads(c.eval(
        "(async()=>{const r=await fetch('/api/api_request',{method:'POST',"
        "headers:{'Content-Type':'application/json'},body:" + repr(json.dumps(body)) +
        "});return JSON.stringify(await r.json());})()", await_promise=True))


print("=== 1. 四大类风格树 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
fam = c.eval("document.querySelectorAll('#vstyleTree .tnode').length")
check("4 大类", fam == 4, f"{fam}")
names = c.eval("Array.from(document.querySelectorAll('#vstyleTree .tlabel')).map(b=>b.textContent)")
check("名称正确", names == ["写实摄影类", "绘画插画类", "卡通动漫类", "3D渲染类"], str(names))
for i, expect in [(0, 11), (1, 11), (2, 10), (3, 10)]:
    c.eval(f"document.querySelectorAll('#vstyleTree .tcaret')[{i}].click()")
    time.sleep(0.5)
    n = c.eval("document.querySelectorAll('#vstyleTree .tsubs .chip').length")
    check(f"{names[i]} 有 {expect} 小类", n == expect, f"{n}")
    c.eval(f"document.querySelectorAll('#vstyleTree .tcaret')[{i}].click()")
    time.sleep(0.4)

print("\n=== 2. 动作是独立选项 ===")
check("有动作下拉", c.eval("!!document.querySelector('#apiAction')"))
opts = c.eval("Array.from(document.querySelectorAll('#apiAction option')).map(o=>o.value)")
check("静态/自然两个选项", opts == ["static", "natural"], str(opts))
_def = c.eval("document.querySelector('#apiAction').querySelector('option[selected]')?.value"
             " || document.querySelector('#apiAction').options[0].value")
check("默认静态（HTML 默认值）", _def == "static", _def)

d_static = ask(with_action=False)
d_action = ask(with_action=True)
seg_s = d_static["user"].split("【构图】")[1].split("【语言】")[0]
seg_a = d_action["user"].split("【构图】")[1].split("【语言】")[0]
check("静态含正面站姿要求", "正对镜头，无表情" in seg_s)
check("静态含双腿分开", "双腿自然微微分开" in seg_s)
check("静态含双手不接触衣料", "双手与衣服边缘保持少量距离" in seg_s)
check("静态无动作叠加", "动作叠加" not in seg_s)
check("自然动作有叠加", "动作叠加" in seg_a)
check("动作版更长", len(seg_a) > len(seg_s), f"{len(seg_a)} vs {len(seg_s)}")

print("\n=== 3. 所有构图默认都是静态站姿 ===")
for comp in ["half_body", "full_body", "front_back", "headshot_plus_front_back"]:
    d = ask(composition=comp)
    seg = d["user"].split("【构图】")[1].split("【语言】")[0]
    # front_back now ships its own stance wording; the others keep STATIC_STANCE.
    mark = "双臂自然垂放于身体两侧" if comp == "front_back" else "正对镜头，无表情"
    check(f"{comp} 含静态站姿", mark in seg)
    check(f"{comp} 无自然动作", "自然动作" not in seg and "动作叠加" not in seg)

print("\n=== 4. 风格驱动人物设计 ===")
photo = ask(visual_style=["photo_portrait"])["user"]
paint = ask(visual_style=["paint_oil"])["user"]
r3d = ask(visual_style=["r3d_real"])["user"]
check("摄影类有介质要求", "【介质要求】" in photo)
check("摄影类要求写实皮肤", "保留真实毛孔" in photo)
check("摄影类禁止插画色块", "禁止出现插画式色块" in photo)
check("绘画类要求笔触表现", "皮肤用笔触与色块表现" in paint)
check("3D类要求次表面散射", "次表面散射" in r3d)
check("无风格时无介质要求", "【介质要求】" not in ask(visual_style=[])["user"])

print("\n=== 5. 风格前缀规则 ===")
check("有前缀规则", "【提示词开头】" in photo)
check("要求以风格短语开头", "必须以视觉风格的英文短语开头" in photo)
mixed = ask(visual_style=["photo_film", "paint_watercolor"])["user"]
check("混合介质有提示", "以第一个介质为主" in mixed, )

print("\n=== 6. 风格块内容 ===")
check("含风格标题", "【视觉风格】" in photo)
check("含风格名", "写实摄影类·人像" in photo)
check("含英文短语", "portrait photograph" in photo)

print("\n=== 7. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
# Grouped layout scrolls #apiControls internally with a sticky action bar, so
# "no overflow" is no longer the invariant — "buttons reachable" is.
check("主按钮常驻可见", c.eval("""(()=>{
  const r = document.querySelector('#btnApiWrite').getBoundingClientRect();
  const p = document.querySelector('.panel').getBoundingClientRect();
  return r.bottom <= p.bottom + 1 && r.top >= p.top;
})()"""))
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
