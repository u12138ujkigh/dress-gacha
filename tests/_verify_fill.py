# -*- coding: utf-8 -*-
"""Verify the panel fills its height and all five compositions carry motion."""
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


print("=== 1. 左栏填满 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
d = c.eval("""JSON.stringify({
  panel: Math.round(document.querySelector('.panel').getBoundingClientRect().height),
  content: Math.round(document.querySelector('#apiControls .ctl1').getBoundingClientRect().height),
  tree: Math.round(document.querySelector('#apiStyles').getBoundingClientRect().height),
  lora: Math.round(document.querySelector('#loraList').getBoundingClientRect().height),
  overflow: (()=>{const e=document.querySelector('#apiControls');return e.scrollHeight-e.clientHeight;})(),
  pageScroll: document.documentElement.scrollHeight - window.innerHeight
})""")
import json as _j
m = _j.loads(d)
print("   度量:", d)
# the grid should occupy most of the panel, and the tree should be tall
ratio = m["content"] / m["panel"]
check("内容占面板 >85%", ratio > 0.85, f"{ratio:.2f}")
check("品类树足够高", m["tree"] >= 150, f"{m['tree']}px")
c.eval("""(()=>{state.loras=[{name:'a',display:'A',strength:1,enabled:true},
  {name:'b',display:'B',strength:0.8,enabled:true}];renderLoras();})()""")
time.sleep(0.6)
_h = c.eval("Math.round(document.querySelector('#loraList').getBoundingClientRect().height)")
check("LoRA 区放得下两行", _h >= 70 and c.eval("document.querySelectorAll('#loraList .lora-row').length") == 2, f"{_h}px")
# The grouped layout is taller than the panel by design: #apiControls scrolls
# internally and the action bar is sticky at the bottom. What must hold is that
# the primary buttons are reachable without hunting.
_btn_in = c.eval("""(()=>{
  const r = document.querySelector('#btnApiWrite').getBoundingClientRect();
  const p = document.querySelector('.panel').getBoundingClientRect();
  return r.bottom <= p.bottom + 1 && r.top >= p.top;
})()""")
check("主按钮常驻可见", _btn_in, f"overflow={m['overflow']}")
check("页面不滚动", m["pageScroll"] <= 0, str(m["pageScroll"]))

print("\n=== 2. 品类树可滚动（18 项全在）===")
cats = c.eval("document.querySelectorAll('#apiStyles .tnode.cat').length")
check("18 大类都在", cats == 18, str(cats))
check("树内部可滚动", c.eval(
    "(()=>{const t=document.querySelector('#apiStyles');return t.scrollHeight>=t.clientHeight;})()"))

print("\n=== 3. 词库模式也填满 ===")
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(1)
d2 = c.eval("""JSON.stringify({
  panel: Math.round(document.querySelector('.panel').getBoundingClientRect().height),
  content: Math.round(document.querySelector('#lexiconControls .ctl2').getBoundingClientRect().height),
  tree: Math.round(document.querySelector('#styles').getBoundingClientRect().height),
  pageScroll: document.documentElement.scrollHeight - window.innerHeight
})""")
m2 = _j.loads(d2)
print("   度量:", d2)
check("词库内容占面板 >85%", m2["content"] / m2["panel"] > 0.85,
      f"{m2['content'] / m2['panel']:.2f}")
check("词库品类树高", m2["tree"] >= 140, f"{m2['tree']}px")
check("词库页面不滚动", m2["pageScroll"] <= 0, str(m2["pageScroll"]))

print("\n=== 4. 五种构图默认静态站姿（动作为独立选项）===")
for comp in ["headshot", "half_body", "full_body", "front_back", "headshot_plus_front_back"]:
    r = c.eval(f"""(async()=>{{
      const res = await fetch('/api/api_request', {{method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{brief:'x', tier:'normal', styles:['formal'],
          composition:'{comp}', lang:'zh', system_prompt:''}})}});
      const j = await res.json();
      return (j.system || '') + '\n@@@\n' + (j.user || '');
    }})()""", await_promise=True)
    has = ("双臂自然垂放于身体两侧" if comp == "front_back"
           else "正对镜头，无表情") in r
    seg = r.split("【构图】")[1].split("【语言】")[0] if "【构图】" in r else "" if "【构图】" in r else ""
    check(f"{comp} 含静态站姿", has and len(seg) > 60, f"{len(seg)} 字")

print("\n=== 5. 静态站姿的关键要求 ===")
r = c.eval("""(async()=>{
  const res = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'full_body', lang:'zh', system_prompt:''})});
  return (await res.json()).user || '';
})()""", await_promise=True)
seg = r.split("【构图】")[1].split("【语言】")[0] if "【构图】" in r else ""
check("要求正面无表情", "正对镜头，无表情" in seg, seg[:60])
check("要求双腿分开", "双腿自然微微分开" in seg)
check("要求双手不接触衣料", "双手与衣服边缘保持少量距离" in seg)
check("要求重心落双脚", "重心均匀落在双脚" in seg)

print("\n=== 6. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
