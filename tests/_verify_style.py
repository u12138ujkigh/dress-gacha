# -*- coding: utf-8 -*-
"""Verify visual styles and the headshot companion prompt."""
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


print("=== 1. 风格树（11 大类 47 小类，可叠加）===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
check("风格树存在", c.eval("!!document.querySelector('#vstyleTree')"))
fam = c.eval("document.querySelectorAll('#vstyleTree .tnode').length")
check("11 大类", fam == 11, f"{fam}")
check("默认未选", c.eval("state.vstyles.length") == 0)
# expand a family and pick two sub-styles to prove stacking
c.eval("document.querySelectorAll('#vstyleTree .tcaret')[0].click()")
time.sleep(0.6)
chips = c.eval("document.querySelectorAll('#vstyleTree .tsubs .chip').length")
check("摄影类展开 9 小类", chips == 9, f"{chips}")
c.eval("document.querySelectorAll('#vstyleTree .tsubs .chip')[3].click()")
time.sleep(0.4)
c.eval("document.querySelector('#vstyleTree .tcaret').click()")
time.sleep(0.6)
c.eval("document.querySelectorAll('#vstyleTree .tcaret')[9].click()")
time.sleep(0.6)
c.eval("document.querySelectorAll('#vstyleTree .tsubs .chip')[0].click()")
time.sleep(0.4)
stacked = c.eval("JSON.stringify(state.vstyles)")
check("可叠加两个", c.eval("state.vstyles.length") == 2, stacked)
check("计数显示", "已选 2" in (c.eval("document.querySelector('#vstyleCount').textContent") or ""))

print("\n=== 2. 风格进入请求 ===")
r = c.eval("""(async()=>{
  const res = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'full_body', lang:'zh', visual_style:['photo_film','light_portrait'], system_prompt:''})});
  return JSON.stringify(await res.json());
})()""", await_promise=True)
import json as _j
d = _j.loads(r)
check("user 含视觉风格块", "【视觉风格】" in d["user"], )
check("风格标签含叠加", "+" in d["visual_style_zh"], d["visual_style_zh"])
check("标注需要大头", d["needs_headshot"] is True)

print("\n=== 3. 大头构图不要求附带大头 ===")
r2 = c.eval("""(async()=>{
  const res = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'headshot', lang:'zh', visual_style:[], system_prompt:''})});
  return JSON.stringify(await res.json());
})()""", await_promise=True)
d2 = _j.loads(r2)
check("大头构图 needs_headshot=False", d2["needs_headshot"] is False)
check("大头构图不含字段要求", "rewritten_prompt_headshot" not in d2["user"])

print("\n=== 4. 预览大头 tab ===")
check("有大头 tab", c.eval("!!document.querySelector('.reqtab.head')"))
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(3)
hidden = c.eval("document.querySelector('.reqtab.head').hidden")
check("全身照时大头 tab 出现", hidden is False, f"hidden={hidden}")
c.eval("document.querySelector('.reqtab.head').click()")
time.sleep(0.5)
val = c.eval("document.querySelector('#apiRequestView').value")
check("大头 tab 有说明", "rewritten_prompt_headshot" in val or "大头" in val, val[:60])
c.eval("document.querySelectorAll('.reqtab')[0].click()")
time.sleep(0.3)

print("\n=== 5. 切大头构图时 tab 隐藏 ===")
c.eval("document.querySelector('#apiComposition').value='headshot';"
       "document.querySelector('#apiComposition').dispatchEvent(new Event('change'))")
time.sleep(2.5)
check("大头构图时 tab 隐藏", c.eval("document.querySelector('.reqtab.head').hidden") is True)
c.eval("document.querySelector('#apiComposition').value='full_body';"
       "document.querySelector('#apiComposition').dispatchEvent(new Event('change'))")
time.sleep(2.5)
check("切回全身 tab 再出现", c.eval("document.querySelector('.reqtab.head').hidden") is False)

print("\n=== 6. 卡片双提示词切换 ===")
made = c.eval("""(()=>{
  const card = {title_zh:'测试·双版本', tier_zh:'正常版',
    prompt:'MAIN PROMPT TEXT', prompt_headshot:'HEADSHOT PROMPT TEXT',
    negative:'x', tier:'normal', style:'formal', seed:null, view:'front', backdrop:'studio'};
  const empty = document.querySelector('#empty'); if (empty) empty.remove();
  document.querySelector('#grid').prepend(cardEl(card, -1));
  return document.querySelectorAll('#grid .card').length;
})()""")
check("注入卡片", made >= 1, str(made))
check("有切换按钮", c.eval("document.querySelectorAll('.card .ptbtn').length") == 2)
check("默认显示构图版", c.eval("document.querySelector('.card .prompt').textContent") == "MAIN PROMPT TEXT")
c.eval("document.querySelectorAll('.card .ptbtn')[1].click()")
time.sleep(0.4)
check("切到大头版", c.eval("document.querySelector('.card .prompt').textContent") == "HEADSHOT PROMPT TEXT")
check("按钮高亮切换", c.eval("document.querySelectorAll('.card .ptbtn')[1].classList.contains('active')"))
c.eval("document.querySelectorAll('.card .ptbtn')[0].click()")
time.sleep(0.4)
check("切回构图版", c.eval("document.querySelector('.card .prompt').textContent") == "MAIN PROMPT TEXT")

print("\n=== 7. 布局未破坏 ===")
d3 = c.eval("""JSON.stringify({
  pageScroll: document.documentElement.scrollHeight - window.innerHeight,
  overflow: (()=>{const e=document.querySelector('#apiControls');return e.scrollHeight-e.clientHeight;})()
})""")
m3 = _j.loads(d3)
check("页面不滚动", m3["pageScroll"] <= 0, str(m3["pageScroll"]))
check("设置区不溢出", m3["overflow"] <= 0, str(m3["overflow"]))
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
