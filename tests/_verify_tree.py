# -*- coding: utf-8 -*-
"""Verify the recursive category tree: pruned for lexicon, full for API."""
from __future__ import annotations

import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from cdp import attach

c = attach()
c.call("Runtime.enable")
c.call("Page.enable")
c.call("Page.reload")
time.sleep(7)

fails = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        fails.append(name)


print("=== 1. 词库模式分类树（覆盖集）===")
check("tree 容器", c.eval("!!document.querySelector('#styles.tree')"))
cats = c.eval("document.querySelectorAll('#styles .tnode.cat').length")
check("只列覆盖的 10 大类", cats == 10, f"{cats} 个")
check("默认收起", c.eval("document.querySelectorAll('#styles .tsubs').length") == 0)
check("计数文案", "大类" in (c.eval("document.querySelector('#styleCount').textContent") or ""),
      c.eval("document.querySelector('#styleCount').textContent"))
check("随机可选", c.eval("!!document.querySelector('#styles > .chip')"))

print("\n=== 2. 展开 / 收起 ===")
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tcaret').click()")
time.sleep(0.5)
subs = c.eval("document.querySelectorAll('#styles .tsubs .chip.sub').length")
check("展开出现小类", subs == 2, f"{subs}")
names = c.eval("Array.from(document.querySelectorAll('#styles .tsubs .chip.sub')).map(e=>e.textContent)")
check("小类名正确", names == ["西式晚礼服", "西式婚纱与婚礼周边"], str(names))
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tcaret').click()")
time.sleep(0.4)
check("再点收起", c.eval("document.querySelectorAll('#styles .tsubs').length") == 0)

print("\n=== 3. 选小类 ===")
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tcaret').click()")
time.sleep(0.4)
c.eval("Array.from(document.querySelectorAll('#styles .tsubs .chip.sub'))[1].click()")
time.sleep(0.4)
check("小类选中", c.eval("document.querySelector('#styles .chip.sub.sel')?.textContent") == "西式婚纱与婚礼周边")
check("展开保持", c.eval("document.querySelectorAll('#styles .tsubs').length") == 1)

print("\n=== 4. 选大类 ===")
c.eval("document.querySelectorAll('#styles .tnode.cat')[3].querySelector('.tlabel').click()")
time.sleep(0.4)
check("大类选中", c.eval("document.querySelector('#styles .tnode.cat.sel .tlabel')?.textContent") == "职业装与行业制服")
check("小类高亮清除", c.eval("!document.querySelector('#styles .chip.sub.sel')"))

print("\n=== 5. 古装只有 2 小类（覆盖集）===")
labels = c.eval("Array.from(document.querySelectorAll('#styles .tnode.cat .tlabel')).map(e=>e.textContent)")
check("有古装与民族服饰", "古装与民族服饰" in labels, str(labels))
idx = labels.index("古装与民族服饰")
c.eval(f"document.querySelectorAll('#styles .tnode.cat')[{idx}].querySelector('.tcaret').click()")
time.sleep(0.4)
hs = c.eval("Array.from(document.querySelectorAll('#styles .tsubs .chip.sub')).map(e=>e.textContent)")
check("古装覆盖 2 小类", len(hs) == 2, str(hs))

print("\n=== 6. API 模式完整树 ===")
c.eval("document.querySelectorAll('.mode-btn')[1].click()")
time.sleep(0.8)
check("API tree 容器", c.eval("!!document.querySelector('#apiStyles.tree')"))
acats = c.eval("document.querySelectorAll('#apiStyles .tnode.cat').length")
check("API 全 18 大类", acats == 18, f"{acats}")
# expand the historical category: 9 subs in the full taxonomy
alabels = c.eval("Array.from(document.querySelectorAll('#apiStyles .tnode.cat .tlabel')).map(e=>e.textContent)")
hidx = alabels.index("古装与民族服饰")
c.eval(f"document.querySelectorAll('#apiStyles .tnode.cat')[{hidx}].querySelector('.tcaret').click()")
time.sleep(0.5)
ahis = c.eval("Array.from(document.querySelectorAll('#apiStyles .tsubs .chip.sub')).map(e=>e.textContent)")
check("API 古装 9 小类", len(ahis) == 9, str(ahis))

print("\n=== 7. API 第18类情趣制服 ===")
ridx = alabels.index("情趣制服与角色扮演")
c.eval(f"document.querySelectorAll('#apiStyles .tnode.cat')[{ridx}].querySelector('.tcaret').click()")
time.sleep(0.5)
arp = c.eval("Array.from(document.querySelectorAll('#apiStyles .tsubs .chip.sub')).map(e=>e.textContent)")
check("情趣 3 小类", len(arp) == 3, str(arp))
c.eval("Array.from(document.querySelectorAll('#apiStyles .tsubs .chip.sub'))[2].click()")
time.sleep(0.4)
check("API 可选小类", c.eval("document.querySelector('#apiStyles .chip.sub.sel')?.textContent") == "材质与剪裁特种设计")

print("\n=== 8. 抽卡：选大类可用 ===")
c.eval("document.querySelectorAll('.mode-btn')[0].click()")
time.sleep(0.4)
# pick 晚礼服与婚庆 (big class) then draw
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tlabel').click()")
time.sleep(0.3)
c.eval("document.querySelector('#count').value='2'")
c.eval("document.querySelector('#btnDraw').click()")
time.sleep(2.8)
cards = c.eval("document.querySelectorAll('#grid .card').length")
check("大类抽卡出卡", cards == 2, f"{cards}")
styles = c.eval("Array.from(document.querySelectorAll('#grid .card .story')).map(e=>e.textContent)")
titles = c.eval("Array.from(document.querySelectorAll('#grid .card-title')).map(e=>e.textContent)")
ok_style = all(("缎面" in t or "婚纱" in t) for t in titles)
check("抽到的确实是该大类下的族", ok_style, str(titles))

print("\n=== 9. 抽卡：选小类可用 ===")
c.eval("document.querySelectorAll('#styles .tnode.cat')[1].querySelector('.tcaret').click()")
time.sleep(0.4)
c.eval("Array.from(document.querySelectorAll('#styles .tsubs .chip.sub'))[1].click()")
time.sleep(0.3)
c.eval("document.querySelector('#btnDraw').click()")
time.sleep(2.8)
t2 = c.eval("Array.from(document.querySelectorAll('#grid .card-title')).map(e=>e.textContent)")
check("小类抽卡命中婚纱", all("婚纱" in t for t in t2), str(t2))

print("\n=== 10. 布局与控制台 ===")
check("无横向溢出", c.eval("document.documentElement.scrollWidth <= window.innerWidth + 2"))
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
