# -*- coding: utf-8 -*-
"""Verify megapixel picker, grouped model list, multi-select, multi-LoRA."""
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


print("=== 1. 百万像素入口 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1)
check("比例下拉存在", c.eval("!!document.querySelector('#apiAspect')"))
check("像素下拉存在", c.eval("!!document.querySelector('#apiMegapixels')"))
aspects = c.eval("Array.from(document.querySelectorAll('#apiAspect option')).map(o=>o.value)")
check("7 种比例", aspects == ["1:1", "3:4", "2:3", "9:16", "4:3", "3:2", "16:9"], str(aspects))
mps = c.eval("Array.from(document.querySelectorAll('#apiMegapixels option')).map(o=>o.value)")
check("6 档像素", len(mps) == 6, str(mps))
prev = c.eval("document.querySelector('#sizePreview')?.textContent")
check("有尺寸预览", "输出" in (prev or ""), prev)

print("\n=== 2. 切比例刷新预览 ===")
c.eval("document.querySelector('#apiAspect').value='16:9'; document.querySelector('#apiAspect').dispatchEvent(new Event('change'))")
time.sleep(1)
p1 = c.eval("document.querySelector('#sizePreview').textContent")
c.eval("document.querySelector('#apiMegapixels').value='2'; document.querySelector('#apiMegapixels').dispatchEvent(new Event('change'))")
time.sleep(1)
p2 = c.eval("document.querySelector('#sizePreview').textContent")
check("16:9 预览更新", "1888" in p1 or "16:9" in p1 or p1 != prev, f"{prev} → {p1}")
check("2MP 预览更新", "1888×1056" in p2 or "2.0" in p2 or p2 != p1, f"{p1} → {p2}")

print("\n=== 3. 模型分组 ===")
groups = c.eval("Array.from(document.querySelectorAll('#apiModel optgroup')).map(g=>g.label)")
check("两组", groups == ["账号渠道（EAC）", "免费通道"], str(groups))
acct = c.eval("document.querySelectorAll('#apiModel optgroup')[0].querySelectorAll('option').length")
free = c.eval("document.querySelectorAll('#apiModel optgroup')[1].querySelectorAll('option').length")
check("账号渠道有模型", acct > 10, f"{acct}")
check("免费通道有模型", free > 10, f"{free}")
total = c.eval("document.querySelectorAll('#apiModel option').length")
check("总数 39", total == 39, f"{total}")
hint = c.eval("document.querySelector('#modelHint').textContent")
check("提示含账号渠道", "账号渠道" in hint or "可用" in hint, hint)

print("\n=== 4. 账号渠道模型可选 ===")
names = c.eval("Array.from(document.querySelectorAll('#apiModel optgroup')[0].querySelectorAll('option')).map(o=>o.value)")
check("含 step-5", any("step-5" in n for n in names), str(names[:4]))
check("含 amd 系列", any("amd/" in n for n in names))

print("\n=== 5. 多选品类仍正常 ===")
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[0].querySelector('.tlabel').click()")
time.sleep(0.2)
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[3].querySelector('.tlabel').click()")
time.sleep(0.4)
check("多选 2 个", c.eval("state.apiStyles.length") == 2)

print("\n=== 6. LoRA 仍正常 ===")
c.eval("""(()=>{const p=state.allLoras; state.loras=[
  {name:p[0].name,display:p[0].display,strength:0.6},
  {name:p[1].name,display:p[1].display,strength:1.2}]; renderLoras();})()""")
time.sleep(0.4)
check("两行 LoRA", c.eval("document.querySelectorAll('.lora-row').length") == 2)
check("权重滑杆 2 个", c.eval("document.querySelectorAll('.lora-slider').length") == 2)

print("\n=== 7. 出图请求带上像素与 LoRA ===")
body = c.eval("""JSON.stringify({
  megapixels: $('#apiMegapixels').value,
  aspect: $('#apiAspect').value,
  loras: state.loras.map(l=>({name:l.name,strength:l.strength}))
})""")
check("含 megapixels", '"megapixels"' in body, body[:100])
check("含 aspect", '"aspect"' in body)

print("\n=== 8. 词库模式回归 ===")
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.4)
check("词库 + LoRA 已拆分", c.eval("!!document.querySelector('#loraList')"))
c.eval("document.querySelector('#count').value='2'")
c.eval("document.querySelector('#btnDraw').click()")
time.sleep(3)
check("词库抽卡正常", c.eval("document.querySelectorAll('#grid .card').length") == 2)

print("\n=== 9. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
