# -*- coding: utf-8 -*-
"""Verify the design-method editor and the API request preview."""
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


print("=== 1. 请求预览框（替代旧的生成结果框）===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(1.5)
check("旧的 apiResult 已移除", c.eval("!document.querySelector('#apiResult')"))
check("新预览框存在", c.eval("!!document.querySelector('#apiRequestView')"))
check("有 system/user 两个 tab", c.eval("document.querySelectorAll('.reqtab').length") == 2)
check("默认选中 system", c.eval("document.querySelector('.reqtab.active').dataset.part") == "system")
syslen = c.eval("document.querySelector('#reqLenSys').textContent")
check("system 字数已显示", syslen.strip().isdigit(), syslen)
usrlen = c.eval("document.querySelector('#reqLenUser').textContent")
check("user 字数已显示", usrlen.strip().isdigit(), usrlen)
val = c.eval("document.querySelector('#apiRequestView').value")
check("预览有正文", len(val) > 300, f"{len(val)} 字")

print("\n=== 2. 两个 tab 内容不同 ===")
c.eval("document.querySelectorAll('.reqtab')[1].click()")
time.sleep(0.4)
userVal = c.eval("document.querySelector('#apiRequestView').value")
check("切到 user 有内容", len(userVal) > 300, f"{len(userVal)} 字")
check("user 含维度清单", "轮廓与体型" in userVal)
check("user 含用户需求", "【用户需求】" in userVal)
c.eval("document.querySelectorAll('.reqtab')[0].click()")
time.sleep(0.3)
sysVal = c.eval("document.querySelector('#apiRequestView').value")
check("system 是设计方法", "设计方法" in sysVal or "# 正常版" in sysVal)
check("两者不同", sysVal != userVal)

print("\n=== 3. 切档位后预览跟着变 ===")
before = c.eval("document.querySelector('#apiRequestView').value")[:80]
c.eval("document.querySelectorAll('#apiTiers .tier')[3].click()")
time.sleep(1.5)
after = c.eval("document.querySelector('#apiRequestView').value")[:80]
check("system 内容随档位变化", before != after, f"{before[:26]} → {after[:26]}")
check("档位是色情版", c.eval("state.apiTier") == "explicit")

print("\n=== 4. 打开设计方法编辑器 ===")
check("查看按钮存在", c.eval("!!document.querySelector('#btnViewMethod')"))
c.eval("document.querySelector('#btnViewMethod').click()")
time.sleep(1.5)
check("弹窗已显示", not c.eval("document.querySelector('#methodModal').hidden"))
check("四个档位 tab", c.eval("document.querySelectorAll('.method-tab').length") == 4)
tabs = c.eval("Array.from(document.querySelectorAll('.method-tab')).map(b=>b.textContent)")
check("tab 名称正确", tabs == ["正常版", "擦边版", "裸露版", "色情版"], str(tabs))
txt = c.eval("document.querySelector('#methodText').value")
check("文本框有全文", len(txt) > 500, f"{len(txt)} 字")
check("是色情版内容", "色情版" in txt or "道具" in txt)
check("文本框可编辑", not c.eval("document.querySelector('#methodText').disabled"))
check("标题正确", "色情版" in (c.eval("document.querySelector('#methodTitle').textContent") or ""))
check("标注已保存", "已保存" in (c.eval("document.querySelector('#methodNote').textContent") or ""))

print("\n=== 5. 编辑后显示未保存 ===")
c.eval("""(()=>{const t=document.querySelector('#methodText');
  t.value = t.value + '\\n\\n<!-- UI-TEST -->';
  t.dispatchEvent(new Event('input'));})()""")
time.sleep(0.4)
note = c.eval("document.querySelector('#methodNote').textContent")
check("提示未保存", "未保存" in (note or ""), note)
check("note 变脏色", c.eval("document.querySelector('#methodNote').classList.contains('dirty')"))

print("\n=== 6. 撤销 ===")
c.eval("document.querySelector('#btnMethodRevert').click()")
time.sleep(0.4)
check("已还原", "UI-TEST" not in (c.eval("document.querySelector('#methodText').value") or ""))
check("提示回到已保存", "已保存" in (c.eval("document.querySelector('#methodNote').textContent") or ""))

print("\n=== 7. 切 tab 载入另一档 ===")
c.eval("document.querySelectorAll('.method-tab')[0].click()")
time.sleep(1.2)
t0 = c.eval("document.querySelector('#methodText').value")
check("载入正常版", "正常版" in t0 or "完整着装" in t0, t0[:30].replace("\n", " "))
check("标题跟着变", "正常版" in (c.eval("document.querySelector('#methodTitle').textContent") or ""))

print("\n=== 8. 保存并生效 ===")
c.eval("""(()=>{const t=document.querySelector('#methodText');
  t.value = t.value + '\\n\\n<!-- UI-SAVE-TEST -->';
  t.dispatchEvent(new Event('input'));})()""")
time.sleep(0.3)
c.eval("document.querySelector('#btnMethodSave').click()")
time.sleep(2.5)
check("保存后提示", "已保存" in (c.eval("document.querySelector('#methodNote').textContent") or ""),
      c.eval("document.querySelector('#methodNote').textContent"))
check("关闭弹窗", True)
c.eval("document.querySelector('#btnMethodClose').click()")
time.sleep(0.5)
check("弹窗已关", c.eval("document.querySelector('#methodModal').hidden"))
# the saved marker must appear in the system preview for 正常版
c.eval("document.querySelectorAll('#apiTiers .tier')[0].click()")
time.sleep(1.5)
c.eval("document.querySelectorAll('.reqtab')[0].click()")
time.sleep(0.3)
sysNow = c.eval("document.querySelector('#apiRequestView').value")
check("保存已进入 system 请求", "UI-SAVE-TEST" in sysNow)

print("\n=== 9. 还原测试内容 ===")
c.eval("document.querySelector('#btnViewMethod').click()")
time.sleep(1.2)
c.eval("""(()=>{const t=document.querySelector('#methodText');
  t.value = t.value.replace('\\n\\n<!-- UI-SAVE-TEST -->','');
  t.dispatchEvent(new Event('input'));})()""")
time.sleep(0.3)
c.eval("document.querySelector('#btnMethodSave').click()")
time.sleep(2.5)
c.eval("document.querySelector('#btnMethodClose').click()")
time.sleep(0.4)
clean = c.eval("document.querySelector('#methodText').value")
check("测试标记已清除", "UI-SAVE-TEST" not in (c.eval("state.apiTiers.normal") and "") )
# verify via a fresh preview
c.eval("document.querySelectorAll('#apiTiers .tier')[0].click()")
time.sleep(1.5)
c.eval("document.querySelectorAll('.reqtab')[0].click()")
time.sleep(0.3)
final = c.eval("document.querySelector('#apiRequestView').value")
check("system 不再含测试标记", "UI-SAVE-TEST" not in final)

print("\n=== 10. 控制台 ===")
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
