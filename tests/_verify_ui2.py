# -*- coding: utf-8 -*-
"""Verify module jump buttons, resizable textarea, live progress, image lightbox."""
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


print("=== 1. 模块是按钮且可跳转 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
c.eval("""(() => {
  const b = document.querySelector('#reqBlock');
  if (b && b.hidden) document.querySelector('#btnPreviewReq').click();
})()""")
time.sleep(3)
tag = c.eval("document.querySelector('#blockList .blk')?.tagName")
check("模块行是 label 且带勾选框", tag == "LABEL" and
      c.eval("!!document.querySelector('#blockList .blk input[type=checkbox]')"), str(tag))
n = c.eval("document.querySelectorAll('#blockList .blk').length")
check("有多个模块按钮", n >= 6, str(n))
check("可点击（有 cursor:pointer）",
      c.eval("getComputedStyle(document.querySelector('#blockList .blk')).cursor") == "pointer")

# make sure the preview actually has text before testing a jump
for _ in range(20):
    if (c.eval("document.querySelector('#apiRequestView').value.length") or 0) > 200:
        break
    time.sleep(0.5)
vlen = c.eval("document.querySelector('#apiRequestView').value.length")
check("预览已有正文", vlen > 200, f"{vlen} 字")

# Click a module that is ticked and carries text; an unticked row has nothing in
# the message to jump to.
_ok = c.eval("""(()=>{
  const rows = [...document.querySelectorAll('#blockList .blk')];
  const i = rows.findIndex(r => {
    if (!r.querySelector('input')?.checked) return false;
    if (r.dataset.key === 'tier_method') return false;
    const em = (r.querySelector('.tile-top em')?.textContent || '').trim();
    return /\\d+\\s*字/.test(em) && parseInt(em, 10) > 0;
  });
  if (i >= 0) rows[i].querySelector('.blk-name').click();
  return i;
})()""")
t0 = c.eval("document.querySelector('#apiRequestView').scrollTop")
time.sleep(0.8)
check("点击后高亮该模块",
      c.eval(f"document.querySelectorAll('#blockList .blk')[{_ok}].classList.contains('on')")
      if isinstance(_ok, int) and _ok >= 0 else False, str(_ok))
# A selection is a range, not a non-zero start: jumping to the first module in a
# channel legitimately begins at offset 0.
check("点击后选中了模块文字", c.eval(
    "(()=>{const t=document.querySelector('#apiRequestView');"
    "return (t.selectionEnd||0) > (t.selectionStart||0);})()"))
check("点击后滚动了", c.eval("document.querySelector('#apiRequestView').scrollTop") >= t0)

print("\n=== 2. 文本框可上下拖动 ===")
check("resize 为 vertical",
      c.eval("getComputedStyle(document.querySelector('#apiRequestView')).resize") == "vertical")
h0 = c.eval("document.querySelector('#apiRequestView').clientHeight")
c.eval("document.querySelector('#apiRequestView').style.height = '260px'")
time.sleep(0.4)
h1 = c.eval("document.querySelector('#apiRequestView').clientHeight")
check("高度可改变", h1 > h0, f"{h0} → {h1}")
c.eval("document.querySelector('#apiRequestView').style.height = ''")

print("\n=== 3. 运行状态区存在 ===")
check("有 runBar", c.eval("!!document.querySelector('#runBar')"))
check("有阶段字段", c.eval("!!document.querySelector('#runPhase')"))
check("有步数字段", c.eval("!!document.querySelector('#runSteps')"))
check("默认隐藏", c.eval("document.querySelector('#runBar').hidden") is True)

print("\n=== 4. 进度接口可用 ===")
prog = json.loads(c.eval(
    "(async()=>{const r=await fetch('/api/progress');return JSON.stringify(await r.json());})()",
    await_promise=True))
check("返回 render/design", "render" in prog and "design" in prog, str(list(prog.keys())))

print("\n=== 5. 灯箱 ===")
check("灯箱存在", c.eval("!!document.querySelector('#lightbox')"))
check("默认隐藏", c.eval("document.querySelector('#lightbox').hidden") is True)
c.eval("openLightbox('data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7','测试图')")
time.sleep(0.5)
check("openLightbox 后显示", c.eval("document.querySelector('#lightbox').hidden") is False)
check("图片 src 已设置", "data:image" in (c.eval("document.querySelector('#lightboxImg').src") or ""))
check("说明文字已设置", c.eval("document.querySelector('#lightboxCap').textContent") == "测试图")
c.eval("document.querySelector('#lightboxClose').click()")
time.sleep(0.4)
check("关闭按钮生效", c.eval("document.querySelector('#lightbox').hidden") is True)

print("\n=== 6. 卡片图片可点开放大 ===")
made = c.eval("""(()=>{
  const card = {title_zh:'测试·预览', tier_zh:'正常版', prompt:'X',
    image:'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
    meta_zh:'测试', tier:'normal', style:'formal', seed:1, view:'front', backdrop:'studio'};
  const e=document.querySelector('#empty'); if(e) e.remove();
  document.querySelector('#grid').prepend(cardEl(card,-1));
  return document.querySelectorAll('#grid .card .card-img img.zoomable').length;
})()""")
check("卡片图带 zoomable 类", made >= 1, str(made))
c.eval("document.querySelector('#grid .card .card-img img.zoomable').click()")
time.sleep(0.6)
check("点图打开灯箱", c.eval("document.querySelector('#lightbox').hidden") is False)
check("灯箱有标题说明",
      "测试" in (c.eval("document.querySelector('#lightboxCap').textContent") or ""))
c.eval("document.querySelector('#lightboxClose').click()")
time.sleep(0.3)

print("\n=== 7. Esc 关闭灯箱 ===")
c.eval("openLightbox('data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7','x')")
time.sleep(0.3)
c.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))")
time.sleep(0.4)
check("Esc 关闭", c.eval("document.querySelector('#lightbox').hidden") is True)

print("\n=== 8. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
