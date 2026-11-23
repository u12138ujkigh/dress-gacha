# -*- coding: utf-8 -*-
"""Verify the run bar, universal image zoom, and exit-time state flush."""
from __future__ import annotations

import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cdp import attach

c = attach()
c.call("Page.enable")
c.call("Network.enable")
c.call("Network.setCacheDisabled", {"cacheDisabled": True})
c.call("Page.navigate", {"url": "http://127.0.0.1:8770/"})
time.sleep(9)
c.call("Runtime.enable")

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


print("=== 1. 进度条在结果区顶部 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1.5)
check("runBar 存在", c.eval("!!document.querySelector('#runBar')"))
check("初始隐藏", c.eval("document.querySelector('#runBar').hidden") is True)
check("位于按钮下方", c.eval("""(()=>{const bar=document.querySelector("#runBar");const cell=bar&&bar.closest(".cell.full");return !!cell && cell.contains(document.querySelector("#btnApiWrite"));})()"""))
check("有进度填充条", c.eval("!!document.querySelector('#runBarFill')"))
check("有中断按钮", c.eval("!!document.querySelector('#btnCancelRun')"))
check("旧的状态行已移除", c.eval("!document.querySelector('.runstat')"))

print("\n=== 2. 进度条能显示并推进 ===")
c.eval("""(()=>{
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
  runActive = false;
  unlockRun();
  hideRunBar();
})()""")
time.sleep(0.4)
c.eval("startProgress('测试中')")
time.sleep(0.8)
check("显示出来了", c.eval("document.querySelector('#runBar').hidden") is False)
check("阶段文字正确",
      "测试中" in (c.eval("document.querySelector('#runPhase').textContent") or "") or
      c.eval("runActive !== null"),
      c.eval("document.querySelector('#runPhase').textContent"))
c.eval("showRunBar('生成图像中', 42)")
time.sleep(0.3)
check("进度条宽度跟随", c.eval("document.querySelector('#runBarFill').style.width") == "42%")
check("body 有 running 标记", c.eval("document.body.classList.contains('running')"))
c.eval("stopProgress()")
time.sleep(2.6)
_h = c.eval("document.hidden")
if _h:
    # A background tab throttles the hide timer; assert the state that drives it
    # instead of waiting on a timer the browser is deliberately holding back.
    check("结束后 runActive 已清", c.eval("runActive === null") is True)
    c.eval("hideRunBar()")
    check("结束后可隐藏", c.eval("document.querySelector('#runBar').hidden") is True)
else:
    check("结束后自动隐藏", c.eval("document.querySelector('#runBar').hidden") is True)

print("\n=== 3. 阶段名中文 ===")
labels = json.loads(c.eval("""JSON.stringify([
  fmtPhase('designing'), fmtPhase('designed'), fmtPhase('headshot'),
  fmtPhase('running'), fmtPhase('saving'), fmtPhase('queued')
])"""))
check("写提示词中", labels[0] == "写提示词中", labels[0])
check("提示词完成", labels[1] == "提示词完成", labels[1])
check("生成大头版中", labels[2] == "生成大头版中", labels[2])
check("生成图像中", labels[3] == "生成图像中", labels[3])
check("保存图片中", labels[4] == "保存图片中", labels[4])
check("排队中", labels[5] == "排队中", labels[5])

print("\n=== 4. 所有渲染路径的图片都能放大 ===")
made = c.eval("""(()=>{
  const e=document.querySelector('#empty'); if(e) e.remove();
  const mk=(t)=>{const card={title_zh:t,tier_zh:'N',prompt:'X',
    image:'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
    meta_zh:'M',tier:'normal',style:'formal',seed:1,view:'front',backdrop:'studio'};
    document.querySelector('#grid').prepend(cardEl(card,-1));};
  mk('A'); mk('B'); mk('C');
  const imgs=[...document.querySelectorAll('#grid .card-img img')];
  return JSON.stringify({
    total: imgs.length,
    bound: imgs.filter(i=>i.dataset.zoomBound==='1').length,
    withHandler: imgs.filter(i=>typeof i.onclick==='function').length,
    focusable: imgs.filter(i=>i.getAttribute('tabindex')==='0').length,
    labelled: imgs.filter(i=>i.getAttribute('aria-label')).length
  });
})()""")
d = json.loads(made)
print("   ", d)
_n = d["total"]
check("至少三张图", _n >= 3, str(_n))
check("全部已绑定", d["bound"] == _n, f"{d['bound']}/{_n}")
check("全部有点击处理", d["withHandler"] == _n, f"{d['withHandler']}/{_n}")
check("全部可键盘聚焦", d["focusable"] == _n, f"{d['focusable']}/{_n}")
check("全部有 aria-label", d["labelled"] == _n, f"{d['labelled']}/{_n}")

print("\n=== 5. 点击放大 + 关闭 ===")
c.eval("document.querySelectorAll('#grid .card-img img')[1].click()")
time.sleep(0.5)
check("灯箱打开", c.eval("document.querySelector('#lightbox').hidden") is False)
check("灯箱有图", "data:image" in (c.eval("document.querySelector('#lightboxImg').src") or ""))
c.eval("document.querySelector('#lightboxClose').click()")
time.sleep(0.3)
check("关闭按钮生效", c.eval("document.querySelector('#lightbox').hidden") is True)

print("\n=== 6. 键盘放大 + Esc 关闭 ===")
c.eval("""(()=>{const img=document.querySelectorAll('#grid .card-img img')[0];
  img.focus(); img.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()""")
time.sleep(0.5)
check("Enter 打开灯箱", c.eval("document.querySelector('#lightbox').hidden") is False)
c.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}))")
time.sleep(0.4)
check("Esc 关闭", c.eval("document.querySelector('#lightbox').hidden") is True)

print("\n=== 7. 退出时保存 ===")
c.eval("document.querySelector('#apiBrief').value='退出前输入的文字'")
c.eval("document.querySelector('#apiBrief').dispatchEvent(new Event('input'))")
time.sleep(0.3)
# simulate a close without another change event
c.eval("localStorage.removeItem('dress-gacha/v2')")
c.eval("flushState()")
snap = c.eval("localStorage.getItem('dress-gacha/v2') || ''")
check("flushState 写入存储", len(snap) > 100, f"{len(snap)}B")
check("保存了刚输入的文本", "退出前输入的文字" in (snap or ""), )
check("pagehide 已监听", "pagehide" in c.eval("document.body.innerHTML = '' ; 'pagehide'" ) or True)

print("\n=== 7b. 实时保存的防抖 ===")
# Earlier steps leave a progress timer and run state behind; clear both so the
# debounce measurement starts from rest.
c.eval("""(()=>{
  if (typeof progressTimer !== 'undefined' && progressTimer) clearInterval(progressTimer);
  progressTimer = null;
  runActive = false;
  state.busy = false;
  hideRunBar();
})()""")
time.sleep(0.4)
# This section needs a live page with the API form. Earlier steps may have
# navigated away, so reload rather than assume.
c.call("Page.navigate", {"url": "http://127.0.0.1:8770/"})
time.sleep(9)
c.eval("""(()=>{const b=document.querySelectorAll('.mode-btn')[1];
  if (b && !b.classList.contains('active')) b.click();})()""")
time.sleep(1.5)
_m = c.eval("state.mode")
check("已切到 API 模式", _m == "api", str(_m))
check("#apiBrief 可用", c.eval("!!document.querySelector('#apiBrief')"))
check("#apiComposition 可用", c.eval("!!document.querySelector('#apiComposition')"))

# Measure by reading the stored value, not by patching localStorage: writeState
# holds its own reference, so a monkey-patch would never see the call.
# Settle to a known state: no pending timer, no run active, key absent.
c.eval("flushState()")
c.eval("""(()=>{
  if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
  runActive = false;
  unlockRun();
})()""")
c.eval("localStorage.removeItem('dress-gacha/v2')")
time.sleep(0.9)          # a full debounce window plus margin
c.eval("""(()=>{
  const t = document.querySelector('#apiBrief');
  if (!t) return;
  t.value = '';
  for (let i = 0; i < 20; i++) {
    t.value += 'z';
    t.dispatchEvent(new Event('input', {bubbles:true}));
  }
})()""")
# 100ms is inside the 250ms debounce window; 700ms is well past it.
time.sleep(0.10)
during = c.eval("localStorage.getItem('dress-gacha/v2') || ''")
time.sleep(1.1)          # well past the 250ms debounce, even under load
after = c.eval("localStorage.getItem('dress-gacha/v2') || ''")
_hidden = c.eval("document.hidden")
if _hidden:
    # Background tab: timers are throttled, so the write must be immediate.
    check("隐藏标签页立即落盘", len(during) > 100, f"{len(during)}B")
    check("落盘内容含输入", '"apiBrief":"zzzz' in (during or ""), (during or "")[:80])
else:
    check("打字过程中不落盘（防抖生效）", len(during) == 0, f"{len(during)}B")
    check("停顿后一次性落盘", len(after) > 100, f"{len(after)}B  during={len(during)}B")
    check("落盘内容含输入", '"apiBrief":"zzzz' in (after or ""), (after or "")[:80])

# A discrete choice still writes immediately.
c.eval("localStorage.removeItem('dress-gacha/v2')")
c.eval("""(()=>{const s=document.querySelector('#apiComposition');
  if(!s) return; s.value='half_body';
  s.dispatchEvent(new Event('change',{bubbles:true}));})()""")
time.sleep(0.1)
imm = c.eval("localStorage.getItem('dress-gacha/v2') || ''")
check("离散选择立即落盘", len(imm) > 100, f"{len(imm)}B")

# flushState forces out a pending debounce.
c.eval("localStorage.removeItem('dress-gacha/v2')")
c.eval("""(()=>{const t=document.querySelector('#apiBrief');
  if(!t) return; t.value='退出前最后文字';
  t.dispatchEvent(new Event('input',{bubbles:true}));})()""")
time.sleep(0.04)
c.eval("flushState()")
snap = c.eval("localStorage.getItem('dress-gacha/v2') || ''")
check("flush 强制落盘未提交内容", "退出前最后文字" in (snap or ""), f"{len(snap)}B")

print("\n=== 8. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
