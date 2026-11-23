# -*- coding: utf-8 -*-
"""Verify state persistence across reload, and LoRA enable/disable."""
from __future__ import annotations

import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cdp import attach

c = attach()
c.call("Runtime.enable")
c.call("Page.enable")

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


def reload_and_wait(sec=9):
    c.call("Page.reload", {"ignoreCache": True})
    time.sleep(sec)


# Start from a clean slate so the checks below prove a real round trip.
c.eval("localStorage.removeItem('dress-gacha/v2')")
reload_and_wait()

print("=== 1. 初始状态为默认 ===")
check("模式为词库", c.eval("state.mode") == "lexicon")
check("LoRA 为空", c.eval("state.loras.length") == 0)

print("\n=== 2. 设定一组选择 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1)
c.eval("document.querySelectorAll('#apiTiers .tier')[2].click()")   # 裸露版
time.sleep(0.3)
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[0].querySelector('.tlabel').click()")
time.sleep(0.2)
c.eval("document.querySelectorAll('#apiStyles .tnode.cat')[17].querySelector('.tlabel').click()")
time.sleep(0.3)
c.eval("document.querySelector('#apiComposition').value='front_back'; document.querySelector('#apiComposition').dispatchEvent(new Event('change'))")
c.eval("document.querySelector('#apiLang').value='zh'; document.querySelector('#apiLang').dispatchEvent(new Event('change'))")
c.eval("document.querySelector('#apiAspect').value='16:9'; document.querySelector('#apiAspect').dispatchEvent(new Event('change'))")
c.eval("document.querySelector('#apiMegapixels').value='2'; document.querySelector('#apiMegapixels').dispatchEvent(new Event('change'))")
c.eval("document.querySelector('#apiBatch').value='7'; document.querySelector('#apiBatch').dispatchEvent(new Event('change'))")
c.eval("document.querySelector('#apiBrief').value='记住这段需求'; document.querySelector('#apiBrief').dispatchEvent(new Event('input'))")
c.eval("""(()=>{const p=state.allLoras; state.loras=[
  {name:p[0].name,display:p[0].display,strength:0.85,enabled:true},
  {name:p[1].name,display:p[1].display,strength:-0.6,enabled:false}];
  renderLoras(); saveState();})()""")
time.sleep(0.8)

snap = c.eval("localStorage.getItem('dress-gacha/v2')")
check("已写入 localStorage", bool(snap) and len(snap) > 100, f"{len(snap) if snap else 0}B")
check("记下 2 个 LoRA", c.eval("state.loras.length") == 2)
check("第二个未勾选", c.eval("state.loras[1].enabled") is False)

print("\n=== 3. 刷新后恢复 ===")
reload_and_wait()
check("模式仍是 API", c.eval("state.mode") == "api",
      c.eval("document.querySelector('.mode-btn.active').dataset.mode"))
check("档位仍是裸露版", c.eval("state.apiTier") == "nude", c.eval("state.apiTier"))
check("品类选中 2 个", c.eval("state.apiStyles.length") == 2, str(c.eval("state.apiStyles")))
check("构图仍为 front_back", c.eval("document.querySelector('#apiComposition').value") == "front_back")
check("语言仍为 zh", c.eval("document.querySelector('#apiLang').value") == "zh")
check("比例仍 16:9", c.eval("document.querySelector('#apiAspect').value") == "16:9")
check("像素仍 2", c.eval("document.querySelector('#apiMegapixels').value") == "2")
check("批量仍 7", c.eval("document.querySelector('#apiBatch').value") == "7")
check("需求文本恢复", c.eval("document.querySelector('#apiBrief').value") == "记住这段需求")
check("LoRA 恢复 2 个", c.eval("state.loras.length") == 2)
check("权重恢复", abs(c.eval("state.loras[0].strength") - 0.85) < 0.001,
      str(c.eval("state.loras[0].strength")))
check("勾选状态恢复", c.eval("state.loras[1].enabled") is False)
check("界面渲染 2 行", c.eval("document.querySelectorAll('.lora-row').length") == 2)
check("第二行带 off 类", c.eval("document.querySelectorAll('.lora-row')[1].classList.contains('off')"))
check("计数显示启用数", "启用 1" in (c.eval("document.querySelector('#loraCount').textContent") or ""),
      c.eval("document.querySelector('#loraCount').textContent"))

print("\n=== 4. 勾选框可切换 ===")
c.eval("document.querySelectorAll('.lora-chk')[1].click()")
time.sleep(0.4)
check("勾上后启用", c.eval("state.loras[1].enabled") is True)
check("off 类移除", not c.eval("document.querySelectorAll('.lora-row')[1].classList.contains('off')"))
check("计数变 2", "启用 2" in c.eval("document.querySelector('#loraCount').textContent"))
c.eval("document.querySelectorAll('.lora-chk')[1].click()")
time.sleep(0.4)
check("再取消", c.eval("state.loras[1].enabled") is False)

print("\n=== 5. 未勾选的不发送 ===")
sent = c.eval("JSON.stringify(state.loras.filter(l=>l.enabled!==false).map(l=>l.name))")
import json as _j
arr = _j.loads(sent)
check("只发 1 个", len(arr) == 1, sent[:120])

print("\n=== 6. 刷新后勾选状态保持 ===")
reload_and_wait()
check("仍未勾选", c.eval("state.loras[1].enabled") is False,
      str(c.eval("state.loras[1].enabled")))
check("权重仍 -0.6", abs(c.eval("state.loras[1].strength") + 0.6) < 0.001,
      str(c.eval("state.loras[1].strength")))

print("\n=== 7. 词库模式也记住 ===")
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.6)
c.eval("document.querySelectorAll('#tiers .tier')[3].click()")
time.sleep(0.3)
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tlabel').click()")
time.sleep(0.3)
c.eval("document.querySelector('#count').value='9'; document.querySelector('#count').dispatchEvent(new Event('change'))")
reload_and_wait()
check("模式回词库", c.eval("state.mode") == "lexicon")
check("档位色情版", c.eval("state.tier") == "explicit", c.eval("state.tier"))
check("品类记住", c.eval("state.style") == "formal", c.eval("state.style"))
check("数量记住 9", c.eval("document.querySelector('#count').value") == "9")

print("\n=== 8. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
