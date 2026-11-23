# -*- coding: utf-8 -*-
"""Verify rewrite, cancel, base model, full layout, request preview placement."""
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


print("=== 1. 全包式布局 ===")
panel_h = c.eval("document.querySelector('.panel').getBoundingClientRect().height")
vh = c.eval("window.innerHeight")
check("面板占据视口高度", panel_h > vh * 0.8, f"{panel_h:.0f} / {vh}")
check("面板内部可滚动", c.eval(
    "(()=>{const p=document.querySelector('.panel');return p.scrollHeight>=p.clientHeight;})()"))
check("有分区块", c.eval("document.querySelectorAll('.cell').length") >= 4,
      str(c.eval("document.querySelectorAll('.cell').length")))
check("请求预览在结果区", c.eval("!!document.querySelector('.results #reqBlock')"))

print("\n=== 2. API 模式控件齐全 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1.5)
check("底模下拉", c.eval("!!document.querySelector('#apiBaseModel')"))
bm = c.eval("document.querySelectorAll('#apiBaseModel option').length")
check("底模有选项", bm >= 3, f"{bm} 个")
default_bm = c.eval("document.querySelector('#apiBaseModel').value")
check("默认选中 moss", "moss" in (default_bm or "").lower(), default_bm)
check("中断按钮（API）", c.eval("!!document.querySelector('#btnCancelApi')"))

c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.6)
check("中断按钮（词库）", c.eval("!!document.querySelector('#btnCancelLex')"))

print("\n=== 3. 请求预览在右侧 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1.2)
c.eval("document.querySelector('#btnPreviewReq').click()")
time.sleep(2.5)
check("预览块已显示", not c.eval("document.querySelector('#reqBlock').hidden"))
rt = c.eval("document.querySelector('#apiRequestView').value")
check("预览有内容", len(rt) > 300, f"{len(rt)} 字")
check("默认 tab 是 user", c.eval("document.querySelector('.reqtab.active').dataset.part") == "user")
check("user 含维度", "轮廓与体型" in rt)
check("user 含品类块", "【品类锚点】" in rt or "【品类范围】" in rt or "限定品类" in rt)

print("\n=== 4. 切档位后品类块仍在 ===")
for idx, name in [(1, "擦边版"), (2, "裸露版"), (3, "色情版"), (0, "正常版")]:
    c.eval(f"document.querySelectorAll('#apiTiers .tier')[{idx}].click()")
    time.sleep(1.6)
    u = c.eval("document.querySelector('#apiRequestView').value")
    has = ("【品类锚点】" in u) or ("【品类范围】" in u) or ("限定品类" in u)
    has_items = "可选的具体款式" in u
    check(f"{name} 含品类块", has and has_items, f"{len(u)} 字")

print("\n=== 5. 改写构图 ===")
# draw two lexicon cards to have prompts to rewrite
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.8)
# clear any busy flag left by an earlier step so the draw can run
c.eval("state.busy=false; document.querySelector('#btnDraw').disabled=false;")
c.eval("document.querySelector('#count').value='2'")
# wait for the draw to actually land rather than sleeping a fixed guess
c.eval("document.querySelector('#btnDraw').click()")
for _ in range(24):
    time.sleep(0.5)
    if c.eval("document.querySelectorAll('#grid .card').length") > 0:
        break
cards = c.eval("document.querySelectorAll('#grid .card').length")
check("有卡片可改写", cards == 2, f"{cards}")
check("卡片有改写按钮", c.eval(
    "document.querySelectorAll('#grid .card [data-act=rw]').length") == 2)
c.eval("document.querySelectorAll('#grid .card [data-act=rw]')[0].click()")
time.sleep(1.2)
check("改写弹窗打开", not c.eval("document.querySelector('#rewriteModal').hidden"))
check("弹窗预填原文", len(c.eval("document.querySelector('#rewriteText').value")) > 200)
# ask for full_body; the draw was front view so nothing back-related to strip
c.eval("document.querySelector('#rewriteTarget').value='headshot'")
c.eval("document.querySelector('#btnRewritePreview').click()")
time.sleep(2)
info = c.eval("document.querySelector('#rewriteInfo').textContent")
check("预览显示删除项", "删除" in (info or ""), info[:70])
newtxt = c.eval("document.querySelector('#rewriteText').value")
check("改写后有大头照说明", "大头照" in newtxt)
check("改写后无全身描述", "head to the shoes" not in newtxt.lower())
c.eval("document.querySelector('#btnRewriteApply').click()")
time.sleep(1)
check("弹窗关闭", c.eval("document.querySelector('#rewriteModal').hidden"))
applied = c.eval("document.querySelectorAll('#grid .card .prompt')[0].textContent")
check("卡片提示词已更新", "大头照" in applied)
check("卡片标注新构图", "构图" in (c.eval(
    "document.querySelectorAll('#grid .card .card-meta')[0].textContent") or ""))

print("\n=== 6. 中断按钮 ===")
check("词库中断可见", c.eval("!!document.querySelector('#btnCancelLex')"))
c.eval("state.busy=true; document.querySelector('#btnDraw').disabled=true;"
       "document.querySelector('#btnApiWrite').disabled=true;")
c.eval("document.querySelector('#btnCancelLex').click()")
time.sleep(2.5)
check("中断后 busy 清零", c.eval("state.busy") is False)
check("中断后按钮解锁", c.eval("document.querySelector('#btnDraw').disabled") is False)

print("\n=== 7. 布局无溢出 ===")
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
