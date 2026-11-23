# -*- coding: utf-8 -*-
"""Verify multi-select categories and multi-LoRA with weights."""
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
time.sleep(8)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


print("=== 1. 页面 ===")
check("ready", c.eval("document.readyState") == "complete")
check("词库 10 大类", c.eval("document.querySelectorAll('#styles .tnode.cat').length") == 10)

print("\n=== 2. API 多选品类 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(0.8)
check("API 18 大类", c.eval("document.querySelectorAll('#apiStyles .tnode.cat').length") == 18)
# pick three categories
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[0].querySelector('.tlabel').click()")
time.sleep(0.2)
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[3].querySelector('.tlabel').click()")
time.sleep(0.2)
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[17].querySelector('.tlabel').click()")
time.sleep(0.4)
sel = c.eval("document.querySelectorAll('#apiStyles .tnode.cat.sel').length")
check("三个大类同时选中", sel == 3, f"{sel}")
check("state 里也是 3 个", c.eval("state.apiStyles.length") == 3, str(c.eval("state.apiStyles")))

print("\n=== 3. 多选可取消 ===")
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[0].querySelector('.tlabel').click()")
time.sleep(0.3)
check("取消一个剩 2", c.eval("state.apiStyles.length") == 2)

print("\n=== 4. 小类也能进多选 ===")
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[17].querySelector('.tcaret').click()")
time.sleep(0.5)
c.eval("Array.from(document.querySelectorAll('#apiStyles .tsubs .chip.sub'))[1].click()")
time.sleep(0.4)
subs_sel = c.eval("Array.from(document.querySelectorAll('#apiStyles .chip.sub.sel')).map(e=>e.textContent)")
check("小类被选中", len(subs_sel) == 1, str(subs_sel))
check("总数 3", c.eval("state.apiStyles.length") == 3, str(c.eval("state.apiStyles")))

print("\n=== 5. 清空 ===")
c.eval("Array.from(document.querySelectorAll('#apiStyles > .chip')).find(e=>e.textContent.includes('清空')).click()")
time.sleep(0.3)
check("清空后为 0", c.eval("state.apiStyles.length") == 0)
check("无高亮", c.eval("document.querySelectorAll('#apiStyles .tnode.cat.sel').length") == 0)

print("\n=== 6. LoRA 多选 ===")
check("LoRA 容器存在", c.eval("!!document.querySelector('#loraList')"))
check("添加按钮存在", c.eval("!!document.querySelector('#btnLoraPick')"))
check("初始为空提示", c.eval("!!document.querySelector('.lora-empty')"))
hint = c.eval("document.querySelector('#loraCount').textContent")
check("计数为未选", hint == "未选", hint)
pool = c.eval("(state.allLoras||[]).length")
check("LoRA 池已载入", pool > 100, f"{pool} 个")

# inject two loras directly (prompt() is not usable from CDP)
c.eval("""(()=>{
  const p = state.allLoras;
  state.loras = [
    {name:p[0].name, display:p[0].display, strength:0.8},
    {name:p[1].name, display:p[1].display, strength:-0.4},
  ];
  renderLoras();
})()""")
time.sleep(0.5)
rows = c.eval("document.querySelectorAll('.lora-row').length")
check("两行 LoRA", rows == 2, f"{rows}")
vals = c.eval("Array.from(document.querySelectorAll('.lora-val')).map(e=>e.textContent)")
check("权重显示", vals == ["0.80", "-0.40"], str(vals))
sliders = c.eval("document.querySelectorAll('.lora-slider').length")
check("两个滑杆", sliders == 2)
check("计数已选 2", c.eval("document.querySelector('#loraCount').textContent") == "已选 2")

print("\n=== 7. 拖滑杆改权重 ===")
c.eval("""(()=>{
  const s = document.querySelectorAll('.lora-slider')[0];
  s.value = '1.35';
  s.dispatchEvent(new Event('input'));
})()""")
time.sleep(0.3)
check("权重已更新", c.eval("state.loras[0].strength") == 1.35, str(c.eval("state.loras[0].strength")))
check("显示同步", c.eval("document.querySelectorAll('.lora-val')[0].textContent") == "1.35")

print("\n=== 8. 移除 LoRA ===")
c.eval("document.querySelectorAll('.lora-del')[1].click()")
time.sleep(0.4)
check("剩 1 个", c.eval("state.loras.length") == 1)
check("行数同步", c.eval("document.querySelectorAll('.lora-row').length") == 1)

print("\n=== 9. 请求体带上多选与 LoRA ===")
body = c.eval("""JSON.stringify({
  styles: state.apiStyles,
  loras: state.loras.map(l=>({name:l.name, strength:l.strength, strength_clip:l.strength, enabled:true}))
})""")
check("能序列化", body and body.startswith("{"), body[:80])

print("\n=== 10. 词库模式未受影响 ===")
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.4)
c.eval("document.querySelector('#count').value='2'")
c.eval("document.querySelector('#btnDraw').click()")
time.sleep(3)
cards = c.eval("document.querySelectorAll('#grid .card').length")
check("词库抽卡正常", cards == 2, f"{cards}")

print("\n=== 11. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
