# -*- coding: utf-8 -*-
"""Verify the revised design dimension order and the clavicle-cropped headshot."""
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


def ask(comp, lang="zh"):
    import json
    return json.loads(c.eval(f"""(async()=>{{
      const r = await fetch('/api/api_request', {{method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{brief:'x', tier:'normal', styles:['formal'],
          composition:'{comp}', lang:'{lang}', visual_style:[], system_prompt:''}})}});
      return JSON.stringify(await r.json());
    }})()""", await_promise=True))


print("=== 1. 设计顺序 ===")
d = ask("full_body")
u = d["user"]
check("有【设计顺序】块", "【设计顺序】" in u)
check("七步顺序", "第一步 体型 → 第二步 面部骨相 → 第三步 五官 → 第四步 皮肤与毛发 → 第五步 妆容 → 第六步 服装 → 第七步 饰品与鞋" in u)
check("说明体型为何第一", "体型与骨相决定整体的好看程度" in u)
check("说明服装要服务体型", "服装最后定" in u)

print("\n=== 2. 体型独立成项且可测量 ===")
check("1 体型（先定这一项）", "1 体型（先定这一项）" in u)
check("头身比", "几头身" in u)
check("腿长占比", "腿长占身高" in u)
check("上下身分割点", "上下身分割点" in u)
check("指尖到达位置", "指尖到达大腿" in u)
check("脚踝粗细", "脚踝粗细" in u)
check("体态", "肩是打开还是内收" in u)

print("\n=== 3. 面部骨相细化 ===")
check("2 面部骨相", "2 面部骨相" in u)
check("脸长宽比", "脸是偏长、偏短还是匀称" in u)
check("发际线形状", "发际线形状" in u)
check("颧弓外轮廓", "颧弓轮廓" in u)
check("苹果肌与法令纹", "苹果肌饱满还是平" in u and "法令纹深浅" in u)
check("下颌角角度", "下颌角是方角还是柔和过渡" in u)
check("下巴后缩", "略后缩" in u or "后缩" in u)
check("侧颜连线", "这条线的起伏" in u)

print("\n=== 4. 五官细化 ===")
check("眼裂长度高度", "眼裂是细长还是圆大" in u)
check("几眼宽", "几眼宽" in u)
check("双眼皮褶皱宽度", "双眼皮褶皱是宽还是窄" in u)
check("卧蚕", "卧蚕有无与大小" in u)
check("鼻翼与眼距比例", "鼻翼宽还是窄" in u)
check("侧面鼻背线条", "侧面鼻背线条" in u)
check("唇峰唇珠", "唇峰清晰还是模糊" in u and "唇珠" in u)
check("人中", "人中长短与深浅" in u)
check("耳朵", "是否贴颅" in u)

print("\n=== 5. 妆容带色号与范围 ===")
check("底妆修容高光", "修容位置与深度" in u and "高光打在哪些点位" in u)
check("眼影晕染范围", "眼影色号与晕染范围" in u)
check("腮红位置", "腮红：色号、位置" in u)
check("持妆状态", "带妆数小时的融妆感" in u)

print("\n=== 6. 大头照只到锁骨 ===")
dh = ask("headshot")
uh = dh["user"]
seg = uh.split("【构图】")[1].split("【语言】")[0]
check("切在锁骨处", "画面下边界切在锁骨处" in seg)
check("只含锁骨以上", "只包含锁骨以上的部分" in seg)
check("肩部以下不入画", "肩部以下不入画" in seg)
check("含颈部与锁骨", "完整头部、颈部与锁骨" in seg)
check("说明无服装主体", "锁骨以上没有服装主体" in seg)
check("大头照不需要附带大头", dh["needs_headshot"] is False)

print("\n=== 7. 大头版由程序另发请求，不写进文本 ===")
check("文本里无字段要求", "rewritten_prompt_headshot" not in u)
check("程序判定需要大头", d["needs_headshot"] is True)

print("\n=== 8. 其他构图未受影响 ===")
for comp in ["half_body", "front_back", "headshot_plus_front_back"]:
    dd = ask(comp)
    s2 = dd["user"].split("【构图】")[1].split("【语言】")[0]
    mark = "双臂自然垂放于身体两侧" if comp == "front_back" else "正对镜头，无表情"
    check(f"{comp} 默认静态站姿", mark in s2, f"{len(s2)} 字")
    check(f"{comp} 不误加锁骨限制", "切在锁骨处" not in s2)

print("\n=== 8b. 裸露档的详细度只管饰品，不管服装层数 ===")
import json as _jj
_n = _jj.loads(c.eval("""(async()=>{
  const r = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'nude', styles:['formal'],
      composition:'full_body', lang:'zh', visual_style:[], char_style:[],
      with_action:false, detail:'ornate', system_prompt:''})});
  return JSON.stringify(await r.json());
})()""", await_promise=True))
_nu = _n["user"]
check("裸露档不写成组衣物", "4–6 件分层" not in _nu)
check("裸露档详细度作用于饰品", "饰品数量：5 件以上" in _nu)
check("裸露档禁止服装层数词", "严禁出现「叠穿」" in _nu)

print("\n=== 8c. 大头照的姿态只讲头颈锁骨 ===")
_h = _jj.loads(c.eval("""(async()=>{
  const r = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'x', tier:'normal', styles:['formal'],
      composition:'headshot', lang:'zh', visual_style:[], char_style:[],
      with_action:true, detail:'normal', system_prompt:''})});
  return JSON.stringify(await r.json());
})()""", await_promise=True))
_hu = _h["user"]
check("大头照不提双腿", "双腿自然微微分开" not in _hu)
check("大头照动作落在头部", "轻轻侧头" in _hu)

print("\n=== 8d. 用户需求是最高优先级 ===")
import json as _jp
_r = _jp.loads(c.eval("""(async()=>{
  const r = await fetch('/api/api_request', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({brief:'穿护士制服', tier:'normal', styles:['historical'],
      composition:'full_body', lang:'zh', visual_style:['photo_portrait'],
      char_style:['cs_gentle'], with_action:false, detail:'normal', system_prompt:''})});
  return JSON.stringify(await r.json());
})()""", await_promise=True))
_ru = _r["user"]
_rs = _r["system"]

check("需求块标为最高优先级", "用户需求 · 最高优先级" in _ru)
check("含优先级规则段", "【优先级规则】" in _ru)
check("规则写明冲突以用户为准", "一律以用户需求为准" in _ru)
check("规则给了古风改护士的例子", "护士制服" in _ru)
check("优先级规则仍在用户消息里", "【优先级规则】" in _ru)
check("非冲突选项仍保留（画风）", "【视觉风格】" in _ru)
check("非冲突选项仍保留（人物风格）", "【人物风格】" in _ru)
check("需求原文保留", "穿护士制服" in _ru)

print("\n=== 9. 布局与控制台 ===")
check("页面不滚动", c.eval("document.documentElement.scrollHeight - window.innerHeight") <= 0)
check("无未捕获错误", c.eval("window.__errs ? window.__errs.length : 0") == 0)

print("\n" + "=" * 56)
if fails:
    print(f"FAILED {len(fails)}: " + "; ".join(fails))
    sys.exit(1)
print("ALL PASSED")
