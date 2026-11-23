# -*- coding: utf-8 -*-
"""Verify the character-style module: tree, stacking, order, persistence."""
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


print("=== 1. 人物风格树 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
check("容器存在", c.eval("!!document.querySelector('#cstyleTree')"))
fams = c.eval("document.querySelectorAll('#cstyleTree .tnode').length")
check("10 大类", fams == 10, str(fams))
names = c.eval("Array.from(document.querySelectorAll('#cstyleTree .tlabel')).map(b=>b.textContent)")
check("含年龄感", "年龄感" in names, str(names[:4]))
check("含动物系", "动物系" in names)
check("含氛围系", "氛围系" in names)
_n = c.eval("state.cstyles.length")
check("选择状态可读（可能已从上次恢复）", isinstance(_n, int), str(_n))

print("\n=== 1b. 画风与人物风格左右并排 ===")
# The pair stacks below 900px by design, so pin a desktop viewport before
# measuring — otherwise the check is testing the narrow-window fallback.
c.call("Emulation.setDeviceMetricsOverride",
       {"width": 1600, "height": 950, "deviceScaleFactor": 1, "mobile": False})
time.sleep(1.5)
geo = json.loads(c.eval("""(()=>{
  const v = document.querySelector('#vstyleTree').getBoundingClientRect();
  const cc = document.querySelector('#cstyleTree').getBoundingClientRect();
  return JSON.stringify({
    vx: Math.round(v.x), vy: Math.round(v.y), vw: Math.round(v.width),
    cx: Math.round(cc.x), cy: Math.round(cc.y), cw: Math.round(cc.width),
    cols: getComputedStyle(document.querySelector('.duo')).gridTemplateColumns
  });
})()"""))
check("两棵树横向并排（同排不同列）",
      geo["cx"] >= geo["vx"] + geo["vw"] - 4 and abs(geo["cy"] - geo["vy"]) < 60,
      f"v=({geo['vx']},{geo['vy']}) c=({geo['cx']},{geo['cy']})")
check("网格两列等宽", geo["vw"] == geo["cw"] and geo["vw"] > 150,
      f"{geo['vw']} / {geo['cw']}")

print("\n=== 2. 展开与选择 ===")
c.eval("document.querySelectorAll('#cstyleTree .tcaret')[0].click()")
time.sleep(0.6)
n = c.eval("document.querySelectorAll('#cstyleTree .tsubs .chip').length")
check("年龄感 7 小类", n == 7, str(n))
labels = c.eval("Array.from(document.querySelectorAll('#cstyleTree .tsubs .chip')).map(b=>b.textContent)")
check("含萝莉/御姐/熟女", all(x in labels for x in ["萝莉", "御姐", "熟女"]), str(labels))
# clear first so the count assertions are deterministic
c.eval("state.cstyles.length = 0; renderCStyles(); saveState();")
time.sleep(0.4)
c.eval("document.querySelectorAll('#cstyleTree .tsubs .chip')[4].click()")
time.sleep(0.4)
check("选中一个", c.eval("state.cstyles.length") == 1, str(c.eval("JSON.stringify(state.cstyles)")))
check("计数更新", "已选 1" in (c.eval("document.querySelector('#cstyleCount').textContent") or ""))

print("\n=== 3. 跨类叠加 ===")
c.eval("document.querySelector('#cstyleTree .tcaret').click()")
time.sleep(0.5)
c.eval("document.querySelectorAll('#cstyleTree .tcaret')[8].click()")
time.sleep(0.6)
c.eval("document.querySelectorAll('#cstyleTree .tsubs .chip')[0].click()")
time.sleep(0.4)
check("两个已选", c.eval("state.cstyles.length") == 2, str(c.eval("JSON.stringify(state.cstyles)")))

print("\n=== 4. 请求里顺序是 画风→人物 ===")
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(3.5)
r = json.loads(c.eval("""(async()=>{
  const res = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'full_body', lang:'zh',
      visual_style:['photo_portrait'], char_style:['cs_oneesan','cs_cat'],
      with_action:false, detail:'normal', system_prompt:''})});
  return JSON.stringify(await res.json());
})()""", await_promise=True))
keys = [b["key"] for b in r["blocks"]]
check("模块含 char_style", "char_style" in keys)
check("画风在人物之前", keys.index("visual_style") < keys.index("char_style"))
check("人物在构图之前", keys.index("char_style") < keys.index("composition"))
check("含【人物风格】", "【人物风格】" in r["user"])
check("标签正确", r.get("char_style_zh") == "年龄感·御姐 + 动物系·猫系", str(r.get("char_style_zh")))

print("\n=== 5. 模块按钮可跳转 ===")
# The block list is only populated once the preview has loaded, and the module
# must be ticked or it has no text in the message to jump to.
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(4)
c.eval("""(()=>{
  const row = document.querySelector('#blockList .blk[data-key=char_style]');
  if (row && !row.querySelector('input').checked) row.querySelector('input').click();
})()""")
for _ in range(12):
    time.sleep(0.6)
    if c.eval("(reqParts.user||'').includes('【人物风格】')"):
        break

check("人物风格已勾选", c.eval("activeBlocks().includes('char_style')"))
check("消息含【人物风格】", c.eval("(reqParts.user||'').includes('【人物风格】')"))

# Click the row's name span: a click on the checkbox would toggle it off.
c.eval("""(()=>{
  const row = document.querySelector('#blockList .blk[data-key=char_style]');
  row.querySelector('.blk-name').click();
})()""")
time.sleep(1.0)
_diag = c.eval("""(()=>{
  const t = document.querySelector('#apiRequestView');
  return JSON.stringify({
    sel: (t.selectionStart||0) + '-' + (t.selectionEnd||0),
    taLen: (t.value||'').length,
    tab: reqTab,
    on: activeBlocks().includes('char_style'),
  });
})()""")
check("点击后有选区", c.eval(
    "(()=>{const t=document.querySelector('#apiRequestView');"
    "return (t.selectionEnd||0) > (t.selectionStart||0);})()"), _diag)

print("\n=== 6. 持久化 ===")
before = c.eval("JSON.stringify(state.cstyles)")
c.call("Page.reload", {"ignoreCache": True})
time.sleep(9)
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
after = c.eval("JSON.stringify(state.cstyles)")
check("刷新后保留", before == after, f"{before} -> {after}")

print("\n=== 7. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
