# -*- coding: utf-8 -*-
"""Verify the one-minute model auto-refresh."""
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


print("=== 1. 定时器已建立 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(2)
check("modelTimer 存在", c.eval("typeof modelTimer !== 'undefined' && modelTimer !== null"))
check("模型已加载", (c.eval("state.models.length") or 0) > 0, str(c.eval("state.models.length")))

print("\n=== 2. 刷新不打断当前选择 ===")
c.eval("""(()=>{
  const s = document.querySelector('#apiModel');
  const opt = Array.from(s.options).find(o => o.value);
  if (opt) s.value = opt.value;
  state.lastPickedModel = s.value;
})()""")
time.sleep(0.3)
picked = c.eval("document.querySelector('#apiModel').value")
check("已选中一个模型", bool(picked), str(picked)[:40])

# force one refresh and confirm the pick survives
import json as _j
before = c.eval("document.querySelector('#apiModel').value")
c.eval("autoRefreshModels()")
time.sleep(4)
after = c.eval("document.querySelector('#apiModel').value")
check("静默刷新后仍选中原模型", before == after, f"{str(before)[:32]} -> {str(after)[:32]}")

print("\n=== 3. 忙碌时不刷新 ===")
c.eval("lockRun('#btnApiWrite')")
c.eval("""(()=>{ window.__f = 0; const of = window.fetch;
  window.fetch = function(u){ if (typeof u==='string' && u.indexOf('/api/models')===0) window.__f++;
    return of.apply(this, arguments); }; })()""")
c.eval("autoRefreshModels()")
time.sleep(2)
n = c.eval("window.__f")
check("busy 时不发请求", n == 0, f"fetches={n}")
c.eval("unlockRun()")

print("\n=== 4. 定时器周期为 60 秒 ===")
check("间隔 60000ms", "setInterval(autoRefreshModels, 60000)" in
      c.eval("startModelAutoRefresh.toString()"))

print("\n=== 5. 下拉框打开时不重建选项 ===")
c.eval("""(()=>{
  window.__pending = null;
  const s = document.querySelector('#apiModel');
  s.focus();
  paintModels();
  window.__pending = s.dataset.pendingOptions || '';
})()""")
time.sleep(0.5)
pend = c.eval("window.__pending")
check("聚焦时把新选项挂起", bool(pend), f"{len(pend or '')} chars pending")

print("\n=== 6. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
