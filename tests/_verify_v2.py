# -*- coding: utf-8 -*-
"""Verify LoRA picker/weights, batch draw, and the three-gateway model list."""
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
time.sleep(10)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


print("=== 1. 三网关模型 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1.5)
groups = c.eval("Array.from(document.querySelectorAll('#apiModel optgroup')).map(g=>g.label)")
check("三组", len(groups) == 3, str(groups))
check("含 WorkBuddy", any("WorkBuddy" in g for g in groups), str(groups))
check("含 EAC", any("EAC" in g for g in groups), str(groups))
total = c.eval("document.querySelectorAll('#apiModel option').length")
check("57 个模型", total == 57, f"{total}")
wb = c.eval("""(()=>{const g=Array.from(document.querySelectorAll('#apiModel optgroup')).find(x=>x.label.includes('WorkBuddy'));
  return g? g.querySelectorAll('option').length : 0;})()""")
check("WorkBuddy 18 个", wb == 18, f"{wb}")
hint = c.eval("document.querySelector('#modelHint').textContent")
check("提示含 WorkBuddy 数", "WorkBuddy" in hint, hint)

print("\n=== 2. LoRA 搜索选择器 ===")
check("搜索框存在", c.eval("!!document.querySelector('#loraSearch')"))
check("下拉容器存在", c.eval("!!document.querySelector('#loraDrop')"))
check("下拉默认隐藏", c.eval("document.querySelector('#loraDrop').hidden"))
c.eval("document.querySelector('#loraSearch').value='3D2D'; document.querySelector('#loraSearch').dispatchEvent(new Event('input'))")
time.sleep(0.6)
check("搜索后展开", not c.eval("document.querySelector('#loraDrop').hidden"))
opts = c.eval("document.querySelectorAll('#loraDrop .lora-opt').length")
check("搜索有结果", opts > 0, f"{opts} 项")
# pick the first
c.eval("document.querySelectorAll('#loraDrop .lora-opt')[0].click()")
time.sleep(0.5)
check("加入一行", c.eval("document.querySelectorAll('.lora-row').length") == 1)
check("选完收起", c.eval("document.querySelector('#loraDrop').hidden"))
check("搜索框清空", c.eval("document.querySelector('#loraSearch').value") == "")

print("\n=== 3. 权重可手填 ===")
check("权重是 number 输入框",
      c.eval("document.querySelector('.lora-val').tagName") == "INPUT" and
      c.eval("document.querySelector('.lora-val').type") == "number")
c.eval("""(()=>{const v=document.querySelector('.lora-val');
  v.value='-1.35'; v.dispatchEvent(new Event('change'));})()""")
time.sleep(0.4)
check("手填生效", abs(c.eval("state.loras[0].strength") + 1.35) < 0.001,
      str(c.eval("state.loras[0].strength")))
c.eval("""(()=>{const v=document.querySelector('.lora-val');
  v.value='9'; v.dispatchEvent(new Event('change'));})()""")
time.sleep(0.4)
check("超范围被夹到 4", abs(c.eval("state.loras[0].strength") - 4) < 0.001,
      str(c.eval("state.loras[0].strength")))
c.eval("""(()=>{const v=document.querySelector('.lora-val');
  v.value='2.75'; v.dispatchEvent(new Event('change'));})()""")
time.sleep(0.4)
check("2.75 保留", abs(c.eval("state.loras[0].strength") - 2.75) < 0.001,
      str(c.eval("state.loras[0].strength")))

print("\n=== 4. 多加一个并调权重 ===")
c.eval("document.querySelector('#loraSearch').value=''; document.querySelector('#loraSearch').dispatchEvent(new Event('input'))")
time.sleep(0.5)
c.eval("document.querySelectorAll('#loraDrop .lora-opt')[0].click()")
time.sleep(0.4)
check("两行", c.eval("document.querySelectorAll('.lora-row').length") == 2)
c.eval("""(()=>{const v=document.querySelectorAll('.lora-val')[1];
  v.value='-0.45'; v.dispatchEvent(new Event('change'));})()""")
time.sleep(0.3)
check("第二个权重独立", abs(c.eval("state.loras[1].strength") + 0.45) < 0.001)
check("计数 2", c.eval("document.querySelector('#loraCount').textContent") == "已选 2")

print("\n=== 5. 批量抽按钮 ===")
check("批量数量输入", c.eval("!!document.querySelector('#apiBatch')"))
check("批量写按钮", c.eval("!!document.querySelector('#btnApiBatchWrite')"))
check("批量写并出图按钮", c.eval("!!document.querySelector('#btnApiBatchRender')"))
check("进度条存在", c.eval("!!document.querySelector('#apiProgress')"))
check("默认 5 条", c.eval("document.querySelector('#apiBatch').value") == "5")

print("\n=== 6. 批量轮换品类 ===")
c.eval("state.apiStyles=['formal','roleplay','scifi']")
picks = c.eval("""JSON.stringify([0,1,2,3,4].map(i=>{
  const l=state.apiStyles; return l.length? [l[i % l.length]] : null;
}))""")
import json as _j
p = _j.loads(picks)
check("轮换有序", p[0] == ["formal"] and p[1] == ["roleplay"] and p[2] == ["scifi"] and p[3] == ["formal"], picks)
c.eval("state.apiStyles=[]")

print("\n=== 7. 像素入口仍在 ===")
check("比例下拉", c.eval("!!document.querySelector('#apiAspect')"))
check("像素下拉", c.eval("!!document.querySelector('#apiMegapixels')"))
check("预览文案", "输出" in (c.eval("document.querySelector('#sizePreview').textContent") or ""))

print("\n=== 8. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
