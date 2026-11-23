# -*- coding: utf-8 -*-
"""LLM client for the API prompt-writing mode.

Message assembly:
    system = tier design method (one of four documents) [+ optional enhancer file]
    user   = design dimensions + style brief + composition rule + lang hint + brief

The model is chosen from the DSH Our Free Model forward listener. Every routable
model is listed; a probe marks which ones actually answer, so the picker can put
the live ones first and the spent ones last instead of failing on 429.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from . import config as _CFG
from . import design as D
from . import taxonomy as _TAX
from . import template_guard as _TG
from . import applog as _LOG

OFM_BASE = os.environ.get("OFM_BASE", "http://127.0.0.1:18899")
OFM_KEY = os.environ.get("OFM_KEY", "")

# The EAC router mirrors the forward listener on its own port and adds the
# account-channel models the plain listener does not route.
EAC_BASE = os.environ.get("EAC_BASE", "http://127.0.0.1:18900")

# WorkBuddy's bridge: an OpenAI-compatible gateway in front of
# copilot.tencent.com, authenticated by its own OAuth token (no key needed).
WORKBUDDY_BASE = os.environ.get("WORKBUDDY_BASE", "http://127.0.0.1:8286")


CHAN_RELAY_BASE = "http://127.0.0.1:18326"

# Ollama: a local model server. It speaks the OpenAI wire format on
# /v1, so it needs no adapter — but it needs NO CREDENTIAL either, and it
# must never be treated as a remote lane: a local model is always reachable
# and always free, so it belongs at the front of the fallback order.
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")

# The context window to request from the local server. Ollama defaults to
# 4096 tokens, which the system prompt alone overruns; the models installed
# here support 262144. 32768 leaves room for the prompt plus a long answer
# without asking the server for a window it cannot hold.
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "32768"))

# The time budget for one local call. The cloud lanes get 180s; a local model
# needs longer because the first call loads the GGUF off disk and the answer
# is generated token by token on this machine.
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "900"))


def _read_relay_key() -> str:
    """Key for the channel-gateway relay, read from the DSH plugin settings.

    The relay is what exposes the channel-pack providers (ByteDance Doubao,
    Qwen, iFlytek Spark and the rest); it refuses every call without this key.
    """
    path = os.path.expanduser(r"~\.dsh\our-free-model\settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            relay = (json.load(f).get("chanGateway") or {}).get("relay") or {}
        if relay.get("enabled") is True:
            return str(relay.get("key") or "")
    except Exception:
        pass
    return ""


def relay_base() -> str:
    """The relay base URL, or "" when the relay is switched off."""
    return CHAN_RELAY_BASE if _read_relay_key() else ""


def _gateways() -> list[tuple[str, str]]:
    """(label, base) for every gateway to ask, in preference order."""
    out = []
    for label, base in (
        ("ofm", OFM_BASE),
        ("eac", EAC_BASE),
        ("workbuddy", WORKBUDDY_BASE),
        ("chan", relay_base()),
        ("ollama", OLLAMA_BASE),
    ):
        base = (base or "").rstrip("/")
        if base and all(base != b for _, b in out):
            out.append((label, base))
    return out


def _read_forward_key() -> str:
    if OFM_KEY:
        return OFM_KEY
    path = os.path.expanduser(r"~\.dsh\our-free-model\settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            return str(json.load(f).get("forwardKey") or "")
    except Exception:
        return ""


# Composition modes → framing instruction
# Every non-headshot composition shares one default stance: the reference pose.
# "Natural action" is NOT baked into each mode any more — it is a separate
# composition option, so a shoot can be posed or unposed by choice.
STATIC_STANCE = (
    "姿态：正对镜头，无表情，面部朝向正前方；双腿自然微微分开约与肩同宽；"
    "双臂自然下垂于身体两侧，双手与衣服边缘保持少量距离、完全不接触衣料；"
    "重心均匀落在双脚，脊柱自然挺直，头部不高不低保持水平。"
)

# The backdrop belongs to the composition, not to the tier: the crop decides
# whether the floor is even in frame, and a tier that hardcoded a background
# would contradict the composition the user actually picked. Lighting stays in
# the tier — the softer tiers want rim light, the explicit one wants hard light.
STUDIO_BACKDROP = (
    "背景：纯色 #E8E8E8 中性浅灰白，无渐变、无纹理、无道具、无环境元素。"
)
STUDIO_FLOOR = (
    "地面：#D8D8D8，仅交代站立接触，无投影方向。"
)

# Which crops show the floor. A headshot cuts at the collarbone and a half
# body at mid-thigh, so neither has any floor in frame.
_FLOOR_MODES = ("full_body", "front_back", "headshot_plus_front_back")

# The clavicle crop shows the head, neck and collarbones only, so a stance that
# talks about legs and weight would be describing things outside the frame.
STATIC_STANCE_HEADSHOT = (
    "姿态：正对镜头，无表情，面部朝向正前方；头部保持水平不高不低，"
    "颈部自然伸展不前倾；双肩放松下沉、不耸起；锁骨保持平展，不抬肩不缩颈。"
    "画面只到锁骨，姿态的全部内容就是头部、颈部与锁骨这三处的相对关系。"
)

# The same crop limit applies to the action variant of a headshot.
ACTION_STANCE_HEADSHOT = (
    "\n\n【动作叠加】在上面的构图与姿态基础上，把静态姿态替换成一个小幅的头部与颈部动作"
    "（轻轻侧头、目光斜向看处、微微收下巴、颈部一侧轻微拉伸、转头时锁骨随之转动），"
    "写清头部转向的角度、下巴的高低、颈部的伸展方向，以及这个动作让发丝与领口如何移动。"
    "动作幅度必须小，不能大到看不清五官，也不需要描述身体动作。"
)

COMPOSITION_MODES = {
    "headshot": (
        "大头照：画面下边界切在锁骨处，只包含锁骨以上的部分——完整头部、颈部与锁骨，"
        "肩部以下不入画。面部占画幅的主要面积，面部结构与妆容细节清晰可辨，85mm 特写，"
        "浅景深。"
        f"{STATIC_STANCE_HEADSHOT}"
        "说明：锁骨以上没有服装主体，服装只以领口或肩带的一小部分出现在画面下缘，"
        "因此这个视角的重点全部落在骨相、五官与妆容上。"
    ),
    "half_body": (
        "半身照：从大腿中部裁切，上半身完整，双手可见，50mm。"
        f"{STATIC_STANCE}"
    ),
    "full_body": (
        "全身照：从头到脚完整入画，双脚可见，85mm 平视。"
        f"{STATIC_STANCE}"
    ),
    "front_back": (
        "一张图被一条竖线分成左右两栏，两栏高度相同、并排齐平，位于同一行，"
        "除此之外画面里没有别的分割线，也没有横线。"
        "左栏是同一个人的全身正面，右栏是这个人的全身背面——画面里只有这一个人，"
        "她以正面和背面各出现一次、共两次；不是两个人，不许出现第二张脸、第二个头。"
        "两栏间距紧凑均衡，人物双臂自然垂放于身体两侧，双手与躯干之间保留间隙。"
        "两栏共用同一套设计、服装、发型、体型与灯光，面部特征完全一致。"
        "\n【左栏：正面全身】从头到脚完整入画，双脚可见；写正面领口与胸腰线条、"
        "正面裙摆或裤型、正面缝线装饰、正面可见配饰、鞋的正面。"
        "\n【右栏：背面全身】同一具身体绕纵轴转 180 度、从背后看：写后脑与发丝走向、"
        "后背开口系带拉链、后腰臀部线条、背面裙摆褶皱、鞋跟与后跟、背面可见配饰。"
        "左栏写过的不在右栏重复。"
        "\n【正反镜像】单侧构件必然换边：正面在人物右腿上的腿环，右栏就在人物左腿；"
        "正面左肩的单肩带，右栏在右肩。腿环、袜带、绑带、臂环、单肩、单侧镂空、"
        "单侧开衩、发辫垂在哪侧、单耳饰、单侧纹身，都要在两栏分别写出它在该侧的位置，"
        "数量、材质、高低完全一致。"
        "\n【人数与姿势（最高优先，覆盖一切）】整张图只有这一个人，全身只出现正面与背面两次。"
        "每栏内部只有一个人，不许出现第二个人、不许把一个人画成两个。"
        "两栏共用同一套姿势：左栏正对镜头、右栏背对镜头、无表情、双腿与肩同宽分开、"
        "双臂自然垂在身体两侧、重心均分双脚、脊柱挺直、头部水平；"
        "右栏保持与左栏完全相同的站姿，只是从背后看，"
        "不许换姿势、不许转身中途、不许坐、不许走路、不许侧身。"
        "任何多出的人、多余的四肢、第二套姿势都算错误。"
    ),
    "headshot_plus_front_back": (
        "一张图被两条竖线分成从左到右三个区，三个区高度相同、并排齐平，位于同一行，"
        "除此之外画面里没有别的分割线，也没有横线。"
        "左区是这个人的大头照，中区是同一个人的全身正面，右区是同一个人的全身背面。"
        "三个区共用同一套设计、服装与灯光，面部特征必须一致。"
        f"{STATIC_STANCE}"
        "\n【左区：大头照】写骨相、五官、妆容、完整发型（从头顶到发尾）、发饰、耳饰、颈饰，切到锁骨以上。"
        "\n【中区：正面全身】写正面领口与胸腰线条、正面裙摆或裤型、"
        "正面缝线装饰、正面可见配饰、鞋的正面。"
        "\n【右区：背面全身】写后脑与发丝走向、后背开口系带拉链、"
        "后腰臀部线条、背面裙摆褶皱、鞋跟与后跟、背面可见配饰。"
        "中区写过的不在右区重复。"
        "\n【正反镜像】背面是同一具身体绕纵轴转 180 度，单侧构件必然换边："
        "正面在人物右腿上的腿环，背面就在人物左腿；正面左肩的单肩带，背面在右肩。"
        "腿环、袜带、绑带、臂环、单肩、单侧镂空、单侧开衩、发辫垂在哪侧、"
        "单耳饰、单侧纹身，都要在中区与右区分别写出它在该区的位置，"
        "数量、材质、高低完全一致。"
        "\n【人数与姿势（最高优先，覆盖一切）】整张图只有这一个人："
        "中区一个全身正面、右区同一个全身背面，全身只出现这两次，左区只多一张脸。"
        "每个区内部只有一个人，不许出现第二个人、不许把一个人画成两个。"
        "三个区共用同一套姿势：正对镜头、无表情、双腿与肩同宽分开、"
        "双臂自然垂在身体两侧、重心均分双脚、脊柱挺直、头部水平；"
        "背面那区保持与正面完全相同的站姿，只是从背后看，"
        "不许换姿势、不许转身中途、不许坐、不许走路、不许侧身。"
        "任何多出的人、多余的四肢、第二套姿势都算错误。"
    ),
    "natural_action": (
        "自然动作：在基本构图之外，额外让角色做一个符合其身份、服装结构与场合的自然动作，"
        "而不是静态站姿。"
        "先想清楚这个角色此刻在做什么——例如迈步时重心落到前脚、裙摆被带起；"
        "一手轻提裙褶；靠墙时一侧肩膀贴住墙面、膝盖微屈；坐下时双腿交叠、手撑在身侧；"
        "整理袖口或腰带；回头时腰部先转；抬手把一缕头发别到耳后。"
        "必须写清重心落在哪条腿、四肢各自的位置、双手分别在做什么，"
        "以及这个动作如何影响衣料（褶皱、拉扯、飘动）。"
        "动作要像被抓拍到的那一下，不是摆好的姿势。"
    ),
    "modifier_natural_action": (
        "\n\n【动作叠加】在上面的构图与姿态基础上，把静态站姿替换成一个自然动作——"
        "按角色的身份、服装结构与场合，让角色处于一个正在发生的动作中"
        "（迈步、提裙、靠墙、坐下、整理衣料、回头等），"
        "写清重心在哪条腿、四肢位置、双手在做什么，以及动作如何影响衣料。"
    ),
}

# The action modifier rewrites the stance, so it is appended rather than
# replacing the composition. Selecting "natural_action" alone means a full-body
# action shot.
ACTION_MODIFIER = COMPOSITION_MODES["modifier_natural_action"]


def compose_composition(composition: str, with_action: bool = False) -> str:
    """Composition text, with the stance either static or in motion.

    The action option REPLACES the static stance rather than adding to it: a
    prompt that says both "face forward, expressionless" and "caught mid-action"
    leaves the model to pick, and it usually picks the static one.

    The backdrop is appended here rather than living in a tier document, so the
    crop and the background can never disagree.
    """
    base = COMPOSITION_MODES.get(composition)
    if base is None:
        base = COMPOSITION_MODES["full_body"]

    setup = STUDIO_BACKDROP
    if composition in _FLOOR_MODES:
        setup += STUDIO_FLOOR

    if not with_action:
        return f"{base}\n{setup}"

    # Drop the static stance sentence for this crop, then append the action.
    stance = STATIC_STANCE_HEADSHOT if composition == "headshot" else STATIC_STANCE
    trimmed = base.replace(stance, "").strip()
    modifier = ACTION_STANCE_HEADSHOT if composition == "headshot" else ACTION_MODIFIER
    return f"{trimmed}{modifier}\n{setup}"


COMPOSITION_LABELS = {
    "headshot": "大头照",
    "half_body": "半身照",
    "full_body": "全身照",
    "front_back": "正反全身照",
    "headshot_plus_front_back": "横向大头+正反全身照",
}

# ---------------------------------------------------------------- visual styles
# The style axis is orthogonal to the category axis: category decides WHAT is
# worn, style decides HOW the picture is made. The taxonomy lives in styles.py
# and supports stacking, because real art direction is a combination:
# "film photography + Hong Kong retro + neon night".
from engine import styles as _STY
from engine import detail as _DT
from engine import prompt_builder as _PB
from engine import charstyle as _CS




def _style_keys(style) -> list[str]:
    if isinstance(style, (list, tuple)):
        return [k for k in style if k]
    return [style] if style and style != "none" else []


def style_label(style) -> str:
    """Human label for a style selection (a key, a list, or nothing)."""
    keys = _style_keys(style)
    return _STY.resolve_multi(keys)[0] if keys else "不指定"


def style_phrase(style) -> str:
    """English clause, used as the PREFIX of the emitted prompt."""
    keys = _style_keys(style)
    return _STY.resolve_multi(keys)[1] if keys else ""


def char_keys(sel) -> list[str]:
    if isinstance(sel, (list, tuple)):
        return [k for k in sel if k]
    return [sel] if sel and sel != "none" else []


def char_label(sel) -> str:
    keys = char_keys(sel)
    return _CS.resolve_multi(keys)[0] if keys else "不指定"


def char_phrase(sel) -> str:
    keys = char_keys(sel)
    return _CS.resolve_multi(keys)[1] if keys else ""


def style_families(style) -> set[str]:
    """Media kinds present in the selection: photographic / drawn / rendered."""
    keys = _style_keys(style)
    if not keys:
        return set()
    fams = _STY.resolve_multi(keys)[2]
    return {_STY.FAMILY_KIND[f] for f in fams if f in _STY.FAMILY_KIND}


# How the character design must change with the medium: skin, makeup, hair and
# fabric all read differently in a photo, a painting, a cartoon and a 3D render.
MEDIUM_DESIGN_HINT = {
    "photographic": (
        "【介质要求】本次输出是摄影作品。人物必须按真人写实标准设计："
        "皮肤保留真实毛孔与细微瑕疵，妆容按真实化妆品色号与施加范围写，"
        "发丝是真实的毛发而非色块，面料按真实纤维的光泽与垂坠描述。"
        "禁止出现插画式色块、赛璐璐阴影、夸张比例或勾线。"
    ),
    "drawn": (
        "【介质要求】本次输出是绘画或插画作品。人物按该绘画语言来设计："
        "五官与人体按该画种的造型习惯简化或夸张，"
        "皮肤用笔触与色块表现而非真实毛孔，妆容用色块与线条概括，"
        "头发按该画种的处理方式（笔触、色块、线稿）描述，面料按画面笔触表现。"
        "同时仍然要给全可执行的骨相与五官数值，让画面有据可依。"
    ),
    "rendered": (
        "【介质要求】本次输出是 3D 渲染作品。人物按三维模型标准设计："
        "皮肤用次表面散射与真实材质参数描述，妆容以贴图与材质层描述，"
        "头发按模型发丝或发片描述，面料按 PBR 材质的粗糙度与光泽描述。"
        "骨相与五官仍按可测量的数值给出，作为建模依据。"
    ),
}

# Phrases each composition owns, so a rewrite can drop the ones that no longer
# apply (asking for a front-only shot must remove the back-view language).
COMPOSITION_MARKERS = {
    "front_back": [
        "back view", "back-view", "backview", "seen from behind", "from behind",
        "rear view", "back panel", "right half", "left half", "right panel",
        "left panel", "two panels", "diptych", "front view on the left",
        "back view on the right", "front and back", "正面", "背面", "正反",
        "并排", "左右各", "双视图", "两栏", "三栏",
    ],
    "headshot_plus_front_back": [
        "three panels", "三栏", "left column", "middle column", "right column",
        "diptych", "back view", "背面", "正反", "并排", "左右各",
    ],
    "headshot": [],
    "half_body": [],
    "full_body": [],
}

# The inverse: language that belongs to a framing and must go when leaving it.
FRAMING_OWN = {
    "full body": ["full body", "full-body", "head to toe", "head to the shoes",
                  "entire figure", "whole figure", "standing full length",
                  "全身", "从头到脚", "双脚"],
    "headshot": ["close-up", "close up", "headshot", "head and shoulders",
                 "大头照", "特写"],
}

# Leftover fragments that only make sense inside a multi-panel layout.
PANEL_RESIDUE = [
    "each panel", "both panels", "each occupying", "occupying half",
    "occupying roughly half", "half of the frame", "half the frame",
    "each taking up", "compact even gap", "narrow even gap",
    "the same woman twice", "same model twice", "twice side by side",
]


def rewrite_composition(prompt: str, target: str, source: str = "") -> dict:
    """Rewrite an existing prompt's framing to `target`.

    The old prompt carries sentences that only make sense for its own framing —
    a front-and-back shot names a back view, a two-panel layout, a left/right
    split. Switching to a single-view composition has to remove those, or the
    model still draws two people.
    """
    import re

    if target not in COMPOSITION_MODES:
        raise ValueError(f"未知构图：{target}")

    text = (prompt or "").strip()
    if not text:
        return {"prompt": COMPOSITION_MODES[target], "removed": [],
                "added": COMPOSITION_MODES[target]}

    multi_target = target in ("front_back", "headshot_plus_front_back")

    drop_terms = []
    # Leaving a multi-panel framing: its markers and its residue go.
    if not multi_target:
        drop_terms.extend(COMPOSITION_MARKERS["front_back"])
        drop_terms.extend(COMPOSITION_MARKERS["headshot_plus_front_back"])
        drop_terms.extend(PANEL_RESIDUE)
        # A framing that named "full body" must lose it when the target is a
        # closer crop, and vice versa.
        if target in ("headshot", "half_body"):
            drop_terms.extend(FRAMING_OWN["full body"])
        if target == "full_body":
            drop_terms.extend(FRAMING_OWN["headshot"])
    else:
        # Staying multi-view: only the competing framing words go.
        if target == "headshot_plus_front_back":
            drop_terms.extend(["diptych", "two panels", "two-panel"])

    drop_terms = list(dict.fromkeys(term for term in drop_terms if term))

    removed = []
    pieces = re.split(r"(?<=[。！？.!?])\s*", text)
    kept_sentences = []
    for sent in pieces:
        if not sent.strip():
            continue
        low = sent.lower()
        if not any(t.lower() in low for t in drop_terms):
            kept_sentences.append(sent)
            continue
        clauses = re.split(r"(?<=[，,；;])\s*", sent)
        survivors = []
        for c in clauses:
            cl = c.lower()
            hits = [t for t in drop_terms if t.lower() in cl]
            if hits:
                removed.extend(hits)
            elif c.strip():
                survivors.append(c.strip())
        if survivors:
            kept = "，".join(survivors) if re.search(r"[\u4e00-\u9fff]", sent) else ", ".join(survivors)
            kept_sentences.append(kept)

    body = " ".join(s.strip() for s in kept_sentences if s.strip())
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r",\s*,", ",", body)
    body = re.sub(r"，\s*，", "，", body)
    body = body.strip(" ，,；;.")
    if body and not body.endswith((".", "。", "!", "！")):
        body += "."

    added = COMPOSITION_MODES[target]
    merged = f"{body} {added}".strip() if body else added

    return {
        "prompt": merged,
        "removed": sorted(set(removed)),
        "added": added,
        "target": target,
        "target_zh": COMPOSITION_LABELS.get(target, target),
    }

# The output language is a system rule placed first so it settles the language
# of the whole answer before the model reads anything else. 中文 is the default;
# the UI also offers an 英文 option. The old per-language hint and the
# "提示词开头" prefix rule are gone.
LANGUAGE_RULE_ZH = (
    "【输出语言】\n"
    "输出语言必须为中文。"
)
LANGUAGE_RULE_EN = (
    "【输出语言】\n"
    "Output language MUST be English. Write the entire answer in English."
)


def language_rule(lang: str) -> str:
    """Pick the system-channel language rule by the requested output language."""
    return LANGUAGE_RULE_EN if (lang or "").strip().lower() in ("en", "english") \
        else LANGUAGE_RULE_ZH


# The four tier documents are user-editable and were written when 中文 was the
# only output language, so they hard-code "rewritten_prompt 必须是中文". With
# the 英文 option picked they would fight the system rule above. Rather than
# rewriting the user's files, adapt a copy in memory at assembly time.
_METHOD_LANG_REPLACEMENTS = (
    ("输出为图像模型可用的中文提示词", "输出为图像模型可用的英文提示词"),
    ("rewritten_prompt 必须是中文", "rewritten_prompt 必须是英文"),
    ("rewritten_prompt 用中文输出", "rewritten_prompt 用英文输出"),
    ("单段中文，无换行", "single paragraph in English, no line breaks"),
    ("50字内中文", "50 words以内英文"),
    ("50 字内中文", "50 words以内英文"),
    ("中文，说明这套设计的三个视觉锚点", "英文，说明这套设计的三个视觉锚点"),
)


def adapt_method_language(text: str, lang: str) -> str:
    """Retarget a tier document's hard-coded 中文 output requirements to English.

    Only touched when the UI asks for English; 中文 mode returns the text
    verbatim. The source files under design_methods/ are never modified.
    """
    if (lang or "").strip().lower() not in ("en", "english"):
        return text
    out = text or ""
    for old, new in _METHOD_LANG_REPLACEMENTS:
        out = out.replace(old, new)
    return out



# ---------------------------------------------------------------- catalog
_catalog_cache: dict = {"at": 0.0, "models": []}
_catalog_lock = threading.Lock()


def _dsh_published_ids() -> set[str] | None:
    """Ids DSH itself publishes through its own forward listeners.

    This is the set the DSH app draws from. The 18326 channel relay exposes the
    whole upstream catalogue (500+ ids, most of which DSH never advertises), so
    listing it directly disagrees with what the user sees in DSH. Reading the
    forward ports keeps the two in step.

    Returns None when no forward port answers, which the caller treats as
    "cannot tell" rather than "empty".
    """
    key = _read_forward_key()
    out: set[str] = set()
    seen_any = False
    for base in (OFM_BASE, EAC_BASE, WORKBUDDY_BASE):
        base = (base or "").rstrip("/")
        if not base:
            continue
        try:
            hdrs = dict(_auth_headers(base, key))
            hdrs["Accept"] = "application/json"
            req = urllib.request.Request(f"{base}/v1/models", headers=hdrs)
            with urllib.request.urlopen(req, timeout=12) as r:
                d = json.loads(r.read().decode("utf-8"))
            seen_any = True
            for m in (d.get("data") or []):
                mid = m.get("id")
                if mid:
                    out.add(mid)
        except Exception:
            continue
    return out if seen_any else None


def _visibility() -> dict:
    """The user's model-visibility choices, as the DSH plugin stores them.

    Three separate controls:
      hiddenModelIds   ids toggled off one by one
      hideFreeModels   hide the free lanes as a group
      hideEacModels    hide the EAC account channel as a group
    Reading them here means this tool's picker matches the DSH page exactly.
    """
    path = os.path.expanduser(r"~\.dsh\our-free-model\settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return {"ids": set(), "free": False, "eac": False}
    ids = d.get("hiddenModelIds")
    return {
        "ids": set(ids) if isinstance(ids, list) else set(),
        "free": d.get("hideFreeModels") is True,
        "eac": d.get("hideEacModels") is True,
    }


def is_hidden(entry: dict, vis: dict) -> bool:
    """Mirror of the plugin's isModelHidden()."""
    if entry.get("id") in vis["ids"]:
        return True
    if vis["free"] and entry.get("channel") in ("free", None, "", "anonymous", "kilo"):
        return True
    if vis["eac"] and entry.get("channel") == "account":
        return True
    return False


def list_models(base: str = "", key: str = "", timeout: float = 10) -> list[dict]:
    """Every model across all gateways, de-duplicated by id.

    A model reachable from several gateways keeps the FIRST gateway that lists
    it, which is the preference order in `_gateways()`.
    """
    key = key or _read_forward_key()
    seen: dict[str, dict] = {}
    targets = [("custom", base)] if base else _gateways()

    # Fetch every gateway's /v1/models in parallel. Serial fetches used to add
    # up (10s × 5 gateways = 40s) whenever a lane was down — the "探测半天"
    # the picker complained about. Results are kept in targets order below so
    # de-duplication still prefers the first gateway that listed a model.
    def _fetch(tgt):
        label, gw = tgt
        try:
            hdrs = dict(_auth_headers(gw, key))
            hdrs["Accept"] = "application/json"
            req = urllib.request.Request(f"{gw}/v1/models", headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            items = data.get("data", []) if isinstance(data, dict) else (data or [])
            return items if isinstance(items, list) else []
        except Exception:
            return []

    if len(targets) > 1:
        results: list[list] = [[] for _ in targets]
        threads = [threading.Thread(
            target=lambda i=i, t=t: results.__setitem__(i, _fetch(t)), daemon=True)
            for i, t in enumerate(targets)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(timeout=timeout + 2)
    else:
        results = [_fetch(t) for t in targets]

    for (label, gw), items in zip(targets, results):
        is_wb = label == "workbuddy"
        for m in items:
            mid = m.get("id") or ""
            if not mid or mid in seen:
                continue
            low = mid.lower()
            is_free = low.endswith(":free") or low.endswith("-free")
            if is_wb:
                channel, source = "workbuddy", "WorkBuddy"
            elif label == "ollama":
                # A locally served model: no account, no quota, no cost.
                channel, source = "local", "本地 Ollama"
            elif label == "chan":
                # A relayed model is a logged-in account provider: ByteDance
                # Doubao, Qwen, iFlytek Spark, Trae, Qoder and friends.
                owner = (m.get("owned_by") or "").strip()
                channel = "chan"
                source = f"渠道网关 · {owner}" if owner else "渠道网关"
            elif label == "eac" and not is_free:
                channel, source = "account", "EAC 账号渠道"
            elif is_free:
                # The free lanes are dropped on purpose: they are slower, rate
                # limited, and weaker than the logged-in account channels that
                # already cover every vendor, so keeping them only adds noise to
                # the picker. Skip the model entirely.
                continue
            else:
                channel, source = "account", "账号渠道"
            # Honour the DSH page's per-model switches and group hides.
            vis = _visibility()
            if mid in vis["ids"]:
                continue
            if vis["free"] and (is_free or channel == "free"):
                continue
            if vis["eac"] and channel == "account":
                continue
            seen[mid] = {
                "id": mid,
                # Ollama ids carry a ":latest" tag that means nothing to the
                # user; the id itself keeps it, because that is what the
                # server expects on the call.
                "name": mid.split("/")[-1].replace(":free", "").replace(":latest", ""),
                "channel": channel,
                "source": source,
                "gateway": gw,
                "context": m.get("context_window"),
                "free": is_free,
            }
    # The ComfyUI text_encoders lane has no /v1/models of its own: its catalog
    # comes from CLIPLoader's object_info and is appended here so the
    # picker shows it as one more group. ComfyUI being down simply yields
    # an empty list.
    try:
        for m in comfyui_local_models():
            if m["id"] not in seen:
                seen[m["id"]] = m
    except Exception:
        pass
    return list(seen.values())


def _auth_headers(gateway: str, key: str) -> dict:
    """Each gateway has its own credential.

    WorkBuddy takes a fixed token; the channel relay takes the key from the
    plugin settings; Ollama takes none at all — it is a local server with no
    accounts, and sending it a bearer token it did not ask for is noise.
    Everything else takes the forward key.
    """
    base = gateway.rstrip("/")
    if base == OLLAMA_BASE.rstrip("/"):
        return {"Content-Type": "application/json"}
    if base == WORKBUDDY_BASE.rstrip("/"):
        return {"Authorization": "Bearer workbuddy", "Content-Type": "application/json"}
    if base == CHAN_RELAY_BASE.rstrip("/"):
        return {"Authorization": f"Bearer {_read_relay_key()}",
                "Content-Type": "application/json"}
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def probe_models(base: str = "", key: str = "", timeout: float = 45,
                 workers: int = 24) -> list[dict]:
    """Mark each model 可用 / 限额 / 不可用 by one tiny completion each.

    Channel-relay models are probed with the same call but a longer budget: a
    relayed provider is reached through the user's logged-in account, so the
    first token can take much longer than a direct free lane.
    """
    key = key or _read_forward_key()
    models = list_models(base=base, key=key)
    if not models:
        return []

    def one(m):
        # A ComfyUI text_encoders model is verified when the lane is listed
        # (ComfyUI up + file present); probing it with a real write takes
        # tens of seconds, so the entry is marked ok directly.
        if m.get("channel") in ("comfyui", "local"):
            # comfyui text_encoders and Ollama models are local lanes: listing
            # them means the backend answered. A real completion probe would
            # force Ollama to load the GGUF into VRAM on first call (slow, and
            # it steals the render GPU), so both are marked ok without a call.
            m["status"] = "ok"
            m["ms"] = 0
            return m
        gw = m.get("gateway") or OFM_BASE
        body = {
            "model": m["id"],
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 4,
            "stream": False,
        }
        if _local_gateway(gw):
            # The probe must use the same window as the real call, and the
            # same endpoint: the OpenAI-shaped route ignores num_ctx and
            # refuses a long prompt, so a probe there could pass while the
            # actual call (far longer) is refused.
            body = _ollama_body(m["id"], [{"role": "user", "content": "hi"}],
                                temperature=0.0, max_tokens=4)
        payload = json.dumps(body).encode()
        url = f"{gw}/api/chat" if _local_gateway(gw) else f"{gw}/v1/chat/completions"
        req = urllib.request.Request(
            url, data=payload, headers=_auth_headers(gw, key),
        )
        # A relayed account model is slower to first token than a free lane.
        budget = timeout * 2 if gw.rstrip("/") == CHAN_RELAY_BASE.rstrip("/") else timeout
        # A local model is slower still on the FIRST call: the GGUF has to be
        # read off disk and loaded into memory before it can answer at all.
        if _local_gateway(gw):
            budget = max(budget, timeout * 3)
        t = time.time()
        try:
            with urllib.request.urlopen(req, timeout=budget) as r:
                r.read(64)
            m["status"] = "ok"
            m["ms"] = int((time.time() - t) * 1000)
        except urllib.error.HTTPError as e:
            # A 401/403 means this gateway wants a credential the plugin holds
            # internally, not that the model is spent.
            m["status"] = "quota" if e.code == 429 else ("denied" if e.code in (401, 403) else "error")
            m["ms"] = int((time.time() - t) * 1000)
        except Exception:
            m["status"] = "error"
            m["ms"] = int((time.time() - t) * 1000)
        return m

    out = []
    lock = threading.Lock()

    def work(queue):
        while True:
            with lock:
                if not queue:
                    return
                m = queue.pop()
            r = one(m)
            with lock:
                out.append(r)

    queue = list(models)
    threads = [threading.Thread(target=work, args=(queue,), daemon=True) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout + 10)

    order = {"ok": 0, "quota": 1, "denied": 2, "error": 3}
    out.sort(key=lambda m: (order.get(m.get("status"), 9), m.get("ms", 9999)))
    with _catalog_lock:
        _catalog_cache["at"] = time.time()
        _catalog_cache["models"] = out
    return out


def cached_probe(max_age: float = 300) -> list[dict]:
    with _catalog_lock:
        if _catalog_cache["models"] and time.time() - _catalog_cache["at"] < max_age:
            return _catalog_cache["models"]
    return probe_models()


_probing = {"running": False, "at": 0.0}


def start_probe_async(base: str = "", key: str = "") -> bool:
    """Kick a probe in the background; returns True if one was started."""
    with _catalog_lock:
        fresh = _catalog_cache["models"] and time.time() - _catalog_cache["at"] < 300
    if fresh or _probing["running"]:
        return False
    _probing["running"] = True

    def run():
        try:
            probe_models(base=base, key=key)
        except Exception:
            pass
        finally:
            _probing["running"] = False
            _probing["at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return True


def list_with_status(base: str = "", key: str = "", timeout: float = 10) -> list[dict]:
    """Fast listing for page open: never wait on slow gateways.

    The comfyui lane comes from an on-disk mirror (zero network) so it appears
    the instant the picker opens. Everything else comes from the catalog cache
    that the background probe fills; we only do a synchronous gateway sweep if
    that cache is still empty (very first call, before the probe has landed).
    Local lanes (comfyui + Ollama) are always ok — no real completion probe.
    """
    key = key or _read_forward_key()
    comfy = comfyui_models_cached()
    with _catalog_lock:
        known = list(_catalog_cache["models"])

    if known:
        # The cache entries already carry probed status; use them directly.
        # Drop stale comfyui entries and take that lane from the disk mirror.
        models = [m for m in known if m.get("channel") != "comfyui"] + comfy
    else:
        # Probe has not produced a catalog yet. Show ONLY the comfyui lane,
        # from the on-disk mirror, with zero network wait. The background probe
        # fills the other lanes, and the page re-pulls a few seconds later.
        # This is the whole point: comfyui is visible the instant the page opens.
        models = list(comfy)

    for m in models:
        if m.get("channel") in ("comfyui", "local"):
            m["status"] = "ok"
            m["ms"] = 0
    order = {"ok": 0, "unknown": 1, "quota": 2, "denied": 3, "error": 4}
    models.sort(key=lambda m: (order.get(m.get("status"), 9), m.get("ms", 99999)))
    return models


def probe_state() -> dict:
    with _catalog_lock:
        return {
            "running": _probing["running"],
            "at": _catalog_cache["at"],
            "count": len(_catalog_cache["models"]),
        }


# ---------------------------------------------------------------- assembly
def load_tier_method(tier: str) -> str:
    """Read the tier's design method from disk on every call.

    Deliberately uncached: the four documents are editable from the UI, and an
    edit must take effect on the next draw without a restart.
    """
    fname = D.TIER_FILES.get(tier)
    if not fname:
        raise ValueError(f"unknown tier: {tier}")
    path = os.path.join(D.DESIGN_DIR, fname)
    with open(path, encoding="utf-8") as f:
        return f.read()


def invalidate_method_cache() -> None:
    """Kept for the save endpoint: nothing is cached, so this is a no-op hook."""
    return None


def resolve_style(style) -> tuple[str, str, str]:
    """Resolve a style selection to (key, brief, items).

    `style` may be one key (category or sub), a list of keys (multi-pick that
    bounds the random range), or 'random'.
    """
    if isinstance(style, (list, tuple)):
        keys = [k for k in style if k]
        if not keys:
            return "random", *_TAX.resolve("random")[1:]
        _l, brief, items = _TAX.resolve_multi(keys)
        return "+".join(keys), brief, items
    key = style if style else "random"
    _l, brief, items = _TAX.resolve(key)
    return key, brief, items


def compose_system(tier: str, style, extra_system: str = "") -> tuple[str, str, str]:
    """Build the system message; returns (system, style_key, style_label_zh)."""
    method = load_tier_method(tier)
    style_key, _brief, _items = resolve_style(style)
    if isinstance(style, (list, tuple)) and style:
        style_zh = _TAX.resolve_multi([k for k in style if k])[0]
    else:
        style_zh = _TAX.resolve(style_key)[0]

    parts = [method.strip()]
    if extra_system.strip():
        block_text, _stats = _TG.compose_template_block(extra_system)
        if block_text:
            parts.append(block_text)
    system = "\n\n---\n\n".join(parts)
    return system, style_key, style_zh


BLOCK_KEYS = ("language", "tier_method", "dimensions", "category", "detail",
              "visual_style", "char_style", "composition", "head_prompt",
              "brief")


# ---------------------------------------------------------------- headshot marker
# The model writes the close-up caption as a hyphen-wrapped segment inside the
# finished prompt. HEAD_PROMPT_RULE is injected into the SYSTEM message; the
# splitter cuts that segment back out so one call yields both versions.
HEAD_PROMPT_TEXT = (
    "单独描述一段人物正面锁骨以上的区域，机位降到与她眼睛齐平并正对画面中心，"
    "头颈保持竖直，鼻尖到下巴的中轴垂直，双眼落在同一条水平线上，双肩放平并与相机平行，"
    "脸与颈肩正对镜头，视线直视镜头。"
    "画面下边界切在锁骨处，只含完整头部、颈部与锁骨，锁骨以下不入画；"
    "必须写完整的头部发型（从发顶、发丝走向到发尾/发髻）与全部发饰，不得只写上半部。"
)

HEAD_PROMPT_RULE = (
    "【大头提示词】\n"
    + HEAD_PROMPT_TEXT + "\n"
    "执行方式：在 rewritten_prompt 的末尾额外附上一段大头照提示词，"
    "整段用一对独立的半角短横线包裹，格式为 -XXX-（短横线与正文之间留一个空格）。\n"
    "这段只写锁骨以上的区域：脸型、五官、妆容、皮肤、耳饰颈饰，"
    "以及完整的头部发型（发顶、发丝走向、刘海、发尾或发髻，从头到尾写全，不许只写上半部）"
    "与全部发饰（头饰、发卡、发簪、发带、耳饰等）；"
    "肩与锁骨只作为画面下缘的裁切边界，服装最多以领口或肩带的一角带过。"
    "胸部以下、身体的下半部分、手臂、腿、鞋与背景地面的描述一律不进入这段。\n"
    "【五官必须与本次人物一致，严禁照抄示例】-XXX- 段里的脸型、眉眼鼻唇、肤色妆容、"
    "发色发质发型、耳饰颈饰与领口，必须是你在 rewritten_prompt 正文里为本次人物"
    "写好的那段描述——同一个人的特写，五官逐字对应正文，不能另换一套。"
    "每次抽卡的人物都不同，本段五官也必须随之不同。"
    "严禁套用任何固定的五官搭配（某种脸型、眼型、鼻型、唇色、发色、发型的套路词），"
    "严禁照抄本规则里示例用的五官词——示例里的五官只是占位符，不是可以照搬的答案。\n"
    "-XXX- 段是 rewritten_prompt 的必填组成部分：任何档位、任何构图都不能省略；"
    "没有这段的输出视为不合格。\n"
    "-XXX- 段必须是整段输出的最后一部分：写完闭合的短横线就立即停止，"
    "后面不得再写任何句子、不得重复已写过的内容、不得另起一段。"
    "尤其不要在结尾续写机位、全身、背面、镜头、构图或任何面部描述——"
    "重复会导致输出失控并被截断。\n"
    "格式示例（只学机位句式和分号分段的写法，到闭合短横线为止不要续写；"
    "方括号里的五官是占位提示，实际输出时要换成你为本次人物写好的五官，不要照抄）："
    "……（正文结尾）。 "
    "-正面直视镜头，机位与眼睛齐平并正对画面中心，脸与颈肩正对镜头，视线直视镜头，"
    "画面下边界切在锁骨处；"
    "[本次人物的脸型][本次人物的眉眼鼻唇]；"
    "[本次人物的完整发型从头顶到发尾][本次人物的全部发饰头饰耳饰]"
    "[本次人物的妆容皮肤][本次人物的颈饰与领口]。-"
)

# 可编辑的大头规则文件：rules/head_prompt.txt。改完即生效，无需改代码/重启。
_RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules")
_HEAD_RULE_FILE = os.path.join(_RULES_DIR, "head_prompt.txt")
_head_rule_cache = {"text": None, "mtime": None}


def load_head_prompt_rule() -> str:
    """读 rules/head_prompt.txt（按 mtime 缓存，热加载）；缺失/出错回退内置常量。"""
    try:
        mtime = os.path.getmtime(_HEAD_RULE_FILE)
        if _head_rule_cache["text"] is not None and _head_rule_cache["mtime"] == mtime:
            return _head_rule_cache["text"]
        with open(_HEAD_RULE_FILE, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
        if not text:
            return HEAD_PROMPT_RULE
        _head_rule_cache["text"] = text
        _head_rule_cache["mtime"] = mtime
        _LOG.info("大头规则已从 rules/head_prompt.txt 热加载 (%d 字)" % len(text))
        return text
    except FileNotFoundError:
        return HEAD_PROMPT_RULE
    except Exception as e:
        _LOG.warn("读取大头规则文件失败，使用内置规则: %s" % e)
        return HEAD_PROMPT_RULE


def _dedupe_repeats(text: str, min_unit: int = 30, repeats: int = 3) -> str:
    """Cut a generation that fell into a repetition loop.

    Small local models (4B int8) can latch onto a fragment of the prompt's
    format example and repeat it verbatim until the token ceiling — one real
    case produced 7800 chars of the same "85mm平视全身，背面背对镜头……"
    sentence and took 190s to generate instead of ~13s. Detect a long window
    recurring back-to-back and truncate at the first occurrence, keeping the
    genuine design and discarding only the loop.
    """
    import re
    from collections import Counter
    if not text or len(text) < min_unit * repeats:
        return text
    # Split into clauses on full stops / semicolons (CN + EN), keep the delim.
    parts = [p for p in re.split(r"(?<=[。；;.!?])", text) if p]
    if len(parts) < repeats:
        return text
    stripped = [p.strip() for p in parts]
    counts = Counter(stripped)
    # A loop is usually TWO long clauses alternating ("-85mm...镜头；" then
    # "窄长的鹅蛋脸...领口。"). Find the longest clause repeated >=repeats
    # times, then cut at its SECOND occurrence — keep one full copy as a
    # natural ending and drop every subsequent repetition.
    dups = [(len(s), s) for s, c in counts.items()
            if c >= repeats and len(s) >= min_unit]
    if not dups:
        return text
    dups.sort(reverse=True)
    unit = dups[0][1]
    seen = 0
    for i, p in enumerate(stripped):
        if p == unit:
            seen += 1
            if seen == 2:
                kept = "".join(parts[:i]).strip()
                return kept or text[:min_unit]
    return text


def split_headshot(prompt: str) -> tuple[str, str]:
    """Cut the -XXX- close-up segment out of a finished prompt.

    Returns (composition_prompt, headshot_prompt). The headshot keeps its
    wrapping hyphens; the composition version is everything else, with the
    separators left behind by the cut tidied up. When no marker is present the
    composition version is the input unchanged and the headshot is "".

    Telling the marker's own hyphens from the ones inside ordinary words is the
    whole difficulty: a real prompt is full of `85mm-lens`, `close-up`,
    `e-commerce`. A marker only STARTS where its hyphen stands alone (it
    follows a space or a separator) and only ENDS where its hyphen also stands
    alone (a space or a separator follows it). Searching for the first
    `-...-` pair instead swallows everything between the first hyphen in the
    text and the last one.

    The common case is a segment at the very END of the prompt, and that is
    checked first because it is unambiguous. A model that puts the segment
    somewhere in the middle is handled by the second pass, which is far more
    careful: the segment has to be long, and the composition left over after
    the cut has to be long too, so a stray ` - ` in prose is not mistaken for
    a marker.
    """
    import re
    text = (prompt or "").strip()
    if not text:
        return text, ""

    def _cut(start: int, close: int):
        """Cut the marker out and tidy the seam."""
        head = text[start:close + 1].strip()
        if not head.strip("-").strip():
            return None
        comp = (text[:start] + text[close + 1:]).strip()
        comp = re.sub(r"[,;，；]\s*[,;，；]+", ", ", comp)
        comp = re.sub(r"\s{2,}", " ", comp)
        comp = comp.strip(" ,;，；.")
        # The marker always comes out of the composition version: leaving it
        # there would feed "-XXX-" to the image model as if it were scene
        # description. Only a composition that is essentially empty keeps the
        # original text — an empty prompt is worse than one that still
        # carries the marker.
        if len(comp) < 5:
            return text, head
        return comp, head

    # ---- pass 1: the marker sits at the very end of the prompt.
    #
    # A hyphen at the very end is a CLOSING boundary, never a mid-word one:
    # a hyphen inside a word (`wedding-dress`) always has letters after it, so
    # it can never match "only separators behind". That is what separates
    # `... headshot-` (a marker) from `... e-commerce` (a word).
    ends = list(re.finditer(r"-(?=[\s,;.。；]*$)", text))
    if ends:
        close = ends[-1].start()
        # The opening hyphen: the nearest one to the left that stands on its
        # own. A hyphen glued to a letter is part of a word, not a delimiter.
        start = -1
        for m in re.finditer(r"(?:(?<=\s)|(?<=[,;.。；:：]))-", text[:close]):
            start = m.start()
        if start >= 0 and close - start >= 2:
            got = _cut(start, close)
            if got:
                return got

    # ---- pass 2: the marker sits somewhere in the middle.
    #
    # Both boundary hyphens must stand alone: the opening one is preceded by
    # a space or a separator, the closing one is followed by a space or a
    # separator. A hyphen inside a word fails both tests, so `85mm-lens` and
    # `e-commerce` are never mistaken for a boundary.
    #
    # Every pair of such hyphens is a candidate, and the LONGEST candidate
    # wins: a close-up segment is a long paragraph, so a short pair between
    # two clauses of prose (` - soft lighting - `) loses to the real one.
    seps = " \t,;.。；:：、，"
    opens, closes = [], []
    for i, ch in enumerate(text):
        if ch != "-":
            continue
        before = text[i - 1] if i else ""
        after = text[i + 1] if i + 1 < len(text) else ""
        if before == "" or before in seps:
            opens.append(i)
        if after == "" or after in seps:
            closes.append(i)
    cands = []
    for close in closes:
        prior = [o for o in opens if o < close]
        if not prior:
            continue
        for start in prior:
            seg = text[start + 1:close].strip()
            if len(seg) < 10:
                continue
            # The segment has to describe a FACE, not a light or a lens. This
            # is the last guard against prose that happens to contain a
            # hyphenated aside.
            if not _looks_like_headshot(seg):
                continue
            cands.append((len(seg), start, close))
    # Longest segment first: the real marker beats any stray hyphen pair.
    cands.sort(reverse=True)
    for _n, start, close in cands:
        got = _cut(start, close)
        if got:
            return got
    return text, ""


# The words a close-up caption is built from. A segment that talks about
# lighting, lenses or backgrounds is prose, not a headshot description.
# The strong words name a face part on their own; the weak ones only count
# together.
_HEADSHOT_STRONG = (
    "face", "facial", "eyebrow", "eyelash", "eyelid", "eyeshadow",
    "makeup", "make-up", "cheekbone", "jawline", "hairline", "bangs",
    "fringe", "earring", "earrings", "freckle", "complexion", "headshot",
    "close-up", "closeup", "portrait",
    "脸", "眼", "眉", "唇", "鼻", "颧", "下巴", "下颌", "额", "妆",
    "耳", "颈", "锁骨", "肤", "眉眼", "五官", "头像", "特写",
)

_HEADSHOT_WEAK = (
    "eye", "brow", "lip", "mouth", "cheek", "chin", "jaw", "forehead",
    "hair", "ear", "neck", "collar", "clavicle", "skin", "mole", "features",
    "发", "发色", "发型",
)


def _looks_like_headshot(seg: str) -> bool:
    """Does this fragment describe a face rather than the scene around it?"""
    low = (seg or "").lower()
    for w in _HEADSHOT_STRONG:
        if w in low:
            return True
    hits = 0
    for w in _HEADSHOT_WEAK:
        if w in low:
            hits += 1
            if hits >= 2:
                return True
    return False

def build_prompt(brief: str, tier: str = "normal", style="random",
                 composition: str = "full_body", lang: str = "en",
                 visual_style="none", with_action: bool = False,
                 detail: str = "normal", extra_system: str = "",
                 char_style="none", enabled_blocks=None) -> _PB.Assembled:
    """Assemble every selected option into ordered, labelled blocks.

    Each option contributes exactly one block, tagged with the channel it belongs
    to. Nothing is written inline: the caller can show the module list, and the
    two messages are just each channel's blocks joined.
    """
    out = _PB.Assembled()

    # ---------------------------------------------------------------- SYSTEM
    # The output language comes FIRST and it is a system rule, not a request.
    # Everything after it is written in a language the model already knows, so
    # the very first thing it reads settles the language of the whole answer.
    out.add(_PB.Block(
        key="language", label="输出语言",
        channel=_PB.SYSTEM, text=language_rule(lang), origin="固定",
    ))

    method = adapt_method_language(load_tier_method(tier), lang)
    out.add(_PB.Block(
        key="tier_method", label="设计档位（设计方法全文）",
        channel=_PB.SYSTEM, text=method, origin=f"档位={tier}",
    ))
    if extra_system.strip():
        block_text, _stats = _TG.compose_template_block(extra_system)
        if block_text:
            out.add(_PB.Block(
                key="extra_template", label="附加提示词模板",
                channel=_PB.SYSTEM,
                text=block_text,
                origin="附加模板",
            ))
    # ---------------------------------------------------------------- USER
    keys = [k for k in style if k] if isinstance(style, (list, tuple)) else (
        [style] if style and style != "random" else [])
    if keys:
        # The selection was already reduced to one concrete sub-class; the model
        # does not choose, it designs that one look.
        label_zh, cat_brief, items = _TAX.resolve_multi(keys)
        scope = "服装（已选定，不可更改）"
        # A concrete pick knows its own style names; use them instead of the
        # whole category's list.
        picked = _TAX.pick_one_sub(keys) if len(keys) > 1 else (
            keys[0] if keys[0] in _TAX.SUB_INDEX else None)
        if picked:
            _cat, _sub = _TAX.SUB_INDEX[picked]
            items = "、".join(x for x in (_sub["items"] or "").split("、") if x)
    else:
        label_zh = "不限（全部分类开放）"
        cat_brief = ("在全部 18 个女装大类中自主选择最贴合用户需求的一类，"
                     "并只按该类的设计语言完成整套造型。")
        items = "（不限定款式，按所选大类的规范自行设计）"
        scope = "服装范围"

    out.add(_PB.Block(
        key="dimensions", label="设计维度与顺序",
        channel=_PB.SYSTEM, text=D.DIMENSIONS_TEXT, origin="固定",
    ))
    out.add(_PB.Block(
        key="category", label="服装选择与款式清单",
        channel=_PB.USER,
        text=(f"【{scope}】{label_zh}\n"
              f"【该服装的设计方向】\n{cat_brief}\n"
              f"【这一类的款式参考（只作为设计依据，最终只做一套）】\n{items}"),
        origin=f"服装={label_zh}",
    ))

    # Nude and explicit tiers remove clothing, so their detail level drives
    # ornament density instead of garment count.
    det = _DT.resolve_for_tier(detail, tier)
    out.add(_PB.Block(
        key="detail", label="服装详细度",
        channel=_PB.SYSTEM, text=det["text"],
        origin=f"详细度={det['zh']}",
    ))

    vphrase = style_phrase(visual_style)
    vlabel = style_label(visual_style)
    fams = style_families(visual_style)
    if vphrase:
        stext = f"【视觉风格】\n{vlabel}\n{vphrase}"
        if len(fams) > 1:
            stext += ("\n注意：这里选了两种以上介质，请以第一个介质为主，"
                      "其余只作为局部影响（如光影或后期），不要让画面变成两者的平均。")
        hints = [MEDIUM_DESIGN_HINT[f] for f in ("photographic", "drawn", "rendered")
                 if f in fams]
        stext += "\n\n" + "\n\n".join(hints) if hints else ""
        out.add(_PB.Block(
            key="visual_style", label="视觉风格与介质约束",
            channel=_PB.SYSTEM, text=stext, origin=f"风格={vlabel}",
        ))

    cphrase = char_phrase(char_style)
    clabel = char_label(char_style)
    if cphrase:
        out.add(_PB.Block(
            key="char_style", label="人物风格",
            channel=_PB.SYSTEM,
            text=(f"【人物风格】\n{clabel}\n{cphrase}\n"
                  "上面这个人物风格决定了比例、五官浓淡、表情、姿态与服装倾向，"
                  "下面所有维度都必须按它来定，不能写成一个与它无关的通用美女。"),
            origin=f"人物风格={clabel}",
        ))

    out.add(_PB.Block(
        key="composition", label="构图与姿态",
        channel=_PB.SYSTEM, text=f"【构图】\n{compose_composition(composition, with_action)}",
        origin=f"构图={COMPOSITION_LABELS.get(composition, composition)}"
               + ("＋自然动作" if with_action else "＋静态站姿"),
    ))

    # The close-up caption is written INSIDE the same call, as its own marked
    # segment: it sits in the system message directly under 构图与姿态, and the
    # splitter cuts it back out of the finished prompt. One API round-trip then
    # yields both the composition version and the headshot version.
    out.add(_PB.Block(
        key="head_prompt", label="大头提示词",
        channel=_PB.SYSTEM, text=load_head_prompt_rule(), origin="固定",
    ))

    # The brief outranks every other option. The precedence rule comes FIRST so
    # the model reads the ranking before it reads the request.
    out.add(_PB.Block(
        key="brief", label="用户需求（最高优先级）",
        channel=_PB.USER,
        text=(
            "【用户需求 · 最高优先级】\n"
            "下面这句用户需求是最高指令。当它与服装、画风、人物风格、服装详细度、"
            "构图、饰品、鞋等任何其它选项冲突时，**一律以用户需求为准**，"
            "被冲突的选项自动让位，不要取折中，也不要两个都写。\n"
            "例如：其它选项选的是古风门派弟子服，而用户写的是护士制服 —— "
            "那就做成护士制服，忽略古风的服装语言。\n"
            "只有当用户没有涉及的维度，才回落到各选项的选择。\n\n"
            f"用户需求：{brief.strip()}\n\n"
            "按系统提示词的四档设计方法与输出契约执行。"
            "只输出 JSON，不要 Markdown 围栏。"
        ),
        origin="一句话需求（最高优先级）",
    ))

    # Only the modules the user left ticked reach the API — 提示词规范/增强
    # (extra_template) included: it is a normal tile in the module list now, so
    # unticking it must drop the template as well.
    if enabled_blocks is not None:
        keep = set(enabled_blocks)
        out.blocks = [b for b in out.blocks if b.key in keep]
    return out


def compose_system(tier: str, style, extra_system: str = "",
                   detail: str = "normal", brief: str = "",
                   composition: str = "full_body", lang: str = "en",
                   visual_style="none", with_action: bool = False):
    """Backwards-compatible wrapper: the SYSTEM channel only."""
    a = build_prompt(brief, tier, style, composition, lang, visual_style,
                     with_action, detail, extra_system)
    style_key, _b, _i = resolve_style(style)
    style_zh = (style_label(style) if visual_style else "")
    return a.system, style_key, _TAX.resolve(style_key)[0] if not isinstance(style, (list, tuple)) or not style else _TAX.resolve_multi([k for k in style if k])[0]


def compose_user(brief: str, style_selection, composition: str, lang: str,
                 visual_style="none", with_action: bool = False,
                 detail: str = "normal") -> str:
    """Backwards-compatible wrapper: the USER channel only."""
    a = build_prompt(brief, "normal", style_selection, composition, lang,
                     visual_style, with_action, detail)
    return a.user


# ---------------------------------------------------------------- call
class _RateLimited(RuntimeError):
    pass


def needs_headshot(composition: str) -> bool:
    """Whether this composition should be paired with a separate close-up.

    A plain program decision: only the headshot composition already IS a
    close-up, so every other composition gets a companion render.
    """
    return composition != "headshot"


def write_headshot_from(main: dict, brief: str = "", model: str = "",
                        tier: str = "normal", style="random",
                        extra_system: str = "", lang: str = "en",
                        visual_style="none", with_action: bool = False,
                        detail: str = "normal", char_style="none",
                        timeout: float = 240) -> dict:
    """Turn the finished composition prompt into a close-up prompt.

    The model does the extraction: it is handed the whole design and told to
    copy the head-visible clauses verbatim while leaving everything below the
    collarbone out. A local string rewrite kept dragging the entire body
    description into the close-up, and letting the model design a second
    character lost the match.
    """
    main_prompt = (main or {}).get("prompt", "").strip()
    if not main_prompt:
        raise ValueError("prompt is empty")

    out = _extract_headshot_by_model(main_prompt, brief=brief, model=model,
                                     tier=tier, style=style, extra_system=extra_system,
                                     lang=lang, visual_style=visual_style,
                                     with_action=with_action, detail=detail,
                                     char_style=char_style, timeout=timeout)
    if out:
        out["source"] = "derived-model"
        return out

    # Model unavailable: fall back to the local rewrite so a close-up still exists.
    derived = _recompose_as_headshot(main_prompt, lang)
    if derived:
        return {
            "prompt": derived,
            "prompt_headshot": derived,
            "tier": tier, "style": style,
            "tier_zh": tier,
            "style_zh": style_label(style),
            "source": "derived-local",
            "model": "local-recompose",
            "wh_ratio": "2:3",
        }

    raise RuntimeError("无法生成大头版提示词")


def _extract_headshot_by_model(main_prompt: str, brief: str = "", model: str = "",
                               tier: str = "normal", style="random",
                               extra_system: str = "", lang: str = "en",
                               visual_style="none", with_action: bool = False,
                               detail: str = "normal", char_style="none",
                               timeout: float = 240) -> dict | None:
    """Ask the model to pull the head-visible half out of a finished prompt.

    The contract is one JSON object with a single `rewritten_prompt` field: the
    close-up caption, nothing else. The model is explicitly told to copy the
    existing wording for hair, face, skin and makeup rather than invent it.
    """
    asm = build_prompt(brief, tier, style, "headshot", lang,
                       visual_style, with_action, detail, extra_system, char_style)
    system, user = asm.system, asm.user
    style_key, _b, _i = resolve_style(style)
    style_zh = style_label(visual_style) if visual_style else _TAX.resolve(style_key)[0]

    extract = (
        "\n\n【任务：从下面这份已定稿的构图版提示词里，提取出大头照提示词】\n"
        f"{main_prompt[:6000]}\n"
        "\n【输出要求】\n"
        "1. 只输出一个 JSON 对象，其中只有 rewritten_prompt 一个字段。\n"
        "2. rewritten_prompt 是这份设计的大头照版本：画幅切在锁骨以上。\n"
        "3. **逐字复制**上面原提示词里关于脸型、五官、眉眼鼻唇、皮肤、毛孔、"
        "发色发质发长刘海与完整发型（发顶、发丝走向、发尾或发髻，从头到尾全部保留，"
        "不许只取上半部）、妆容、耳饰颈饰、头饰发饰发卡发簪发带、领口的描述——"
        "不要改写、不要概括、不要补充原文没有的细节。\n"
        "4. **删除**锁骨以下的一切：全身、腿、臀、腰、胸围、裙、裤、袜、鞋、"
        "脚踝、手臂、手、姿势、重心、站姿、背面描述、镜像、左右分栏、"
        "分割线、材质参数、光线与背景的句子。\n"
        "5. 保留原提示词开头的视觉风格短语、材质渲染词和镜头语言。\n"
        "6. 不要出现「panel」「turnaround」「四宫格」「拼图」「multiple views」这类词。\n"
        "7. 长度控制在原提示词的 20%–35%，只留大头照真正需要的描写。"
    )
    # The close-up companion is part of the same answer, so it follows the
    # selected output language (see language_rule()).
    extract += ("\n8. Output rewritten_prompt in English."
                if (lang or "").strip().lower() in ("en", "english")
                else "\n8. rewritten_prompt 用中文输出。")

    out = _run_lanes(system, user + extract, model=model, timeout=timeout,
                     tier=tier, style_key=style_key, style_zh=style_zh,
                     visual_style=visual_style, composition="headshot")
    hp = (out.get("prompt") or out.get("rewritten_prompt") or "").strip()
    if not hp:
        return None
    # The model may still leave body words in; drop the obvious ones.
    hp = _strip_body_from_headshot(hp)
    if len(hp) < 40:
        return None
    out["prompt"] = hp
    out["prompt_headshot"] = hp
    return out


# Body words that must not survive into a close-up caption.
_BODY_WORDS = (
    "full-body", "full body", "turnaround", "panel", "panels", "diptych",
    "thigh", "thighs", "knees", "calves", "ankles", "hips", "waist", "bust",
    "skirt", "socks", "pumps", "stiletto", "garter", "hem", "pleats",
    "petticoat", "bodice", "spine", "weight even", "stance", "mirrored",
    "split screen", "contact sheet", "character sheet", "quad",
)


def _strip_body_from_headshot(text: str) -> str:
    """Remove whole clauses that describe the body below the collarbone."""
    import re
    parts = [p.strip() for p in re.split(r"(?<=[,;，；])\s*", text) if p.strip()]
    kept = [p.rstrip(" ,;，；") for p in parts
            if not any(w in p.lower() for w in _BODY_WORDS)]
    out = ", ".join(kept)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r",\s*,+", ",", out).strip(" ,;，；")
    return out or text.strip()

# Markers that begin the composition / framing part of a prompt. Everything from
# the earliest match onward is replaced for a close-up.
_FRAME_MARKERS = (
    "full-body portrait", "full body portrait", "full-body shot",
    "full body", "full-body", "whole body", "entire figure", "head to toe",
    "half-body", "half body", "waist-up", "knee-up",
    "wide shot", "medium shot", "cowboy shot",
    "two panels", "two-panel", "three panels", "three-panel", "diptych",
    "side by side", "left half", "right half", "left panel", "right panel",
    "front view on the left", "back view on the right",
    "standing ", "posed against", "framed from",
    "camera at", "shot at eye level", "85mm prime lens", "85mm lens",
    "composition:", "framing:", "seamless light grey studio",
    "seamless grey studio", "studio backdrop",
)

# Sentences that only make sense in a multi-panel or full-body layout. They are
# removed from the character half even when no cut point was found.
_MULTI_RESIDUE = (
    "two panels", "three panels", "two-panel", "three-panel", "diptych",
    "side by side", "left half", "right half", "left panel", "right panel",
    "left column", "right column", "middle column",
    "front view", "back view", "seen from behind", "rear view",
    "same stance", "same person", "same woman", "same model",
    "both panels", "each panel", "occupying half", "half of the frame",
)


# Framing words that may appear EARLY in a prompt without ending the character
# description. Cutting on these threw away everything after them — a prompt that
# opened with "side-by-side full-body front panel and back panel of the same
# woman, ... hair ..., ... skirt ..., ... thigh ring ..." lost the character.
_EARLY_FRAME = (
    "side-by-side", "side by side", "two panels", "three panels", "diptych",
    "full-body", "full body", "whole body", "head to toe",
    "front panel", "back panel", "front view", "back view",
    "left half", "right half", "left panel", "right panel",
    "vertical-axis turnaround", "turnaround", "character sheet",
)

# Framing words that reliably BEGIN the camera part of a prompt.
_LATE_FRAME = (
    "camera at", "shot at eye level", "eye-level", "85mm", "50mm", "35mm",
    "composition:", "framing:", "light:", "background:", "backdrop",
    "key light", "rim light", "fill light",
)


def _find_cut(text: str) -> int:
    """Index where the camera/framing part starts, or -1.

    Only a LATE marker ends the character half. Early layout words are skipped:
    they usually sit inside the character sentence, and cutting there deletes
    the design itself.
    """
    low = text.lower()
    best = -1
    for mk in _LATE_FRAME:
        i = low.find(mk)
        if i > 120 and (best < 0 or i < best):
            best = i
    return best


def _strip_multi(text: str) -> str:
    """Remove sentences/clauses that only make sense in a multi-panel layout."""
    import re
    out = []
    for sent in re.split(r"(?<=[.!?。！？;；])\s*", text):
        if not sent.strip():
            continue
        sl = sent.lower()
        if any(t in sl for t in _MULTI_RESIDUE):
            clauses = re.split(r"(?<=[,;，；])\s*", sent)
            kept = [c.strip() for c in clauses
                    if c.strip() and not any(t in c.lower() for t in _MULTI_RESIDUE)]
            if kept:
                out.append(", ".join(kept))
            continue
        out.append(sent.strip())
    joined = " ".join(out)
    joined = re.sub(r"\s{2,}", " ", joined)
    joined = re.sub(r",\s*,+", ",", joined)
    return joined.strip(" ,;，；.")


# Phrase-level scrubbers. Multi-panel wording is replaced in place rather than
# deleted by clause: the offending clause usually also carries the subject
# ("... of the same adult Chinese woman"), so cutting it threw away the design.
_PANEL_SCRUB = (
    # multi-view / layout jargon
    (r"\bside[\s-]*by[\s-]*side\b", ""),
    (r"\bvertical[\s-]*axis\s+turnaround\b", ""),
    (r"\bturnaround\b", ""),
    (r"\bcharacter\s+sheet\b", ""),
    (r"\bcontact\s+sheet\b", ""),
    (r"\bdiptych\b", ""),
    (r"\b(two|three|four)[\s-]*panel(s)?\b", ""),
    (r"\b(two|three|four)\s+panels?\b", ""),
    (r"\b(two|three|four)\s+views?\b", ""),
    (r"\b(in|shown\s+in)\s+panels?\b", ""),
    # panel references — keep any trailing nouns that describe the figure
    (r"\b(front|back)\s+panel\s+and\s+(front|back)\s+panel\b", ""),
    (r"\bthe\s+(front|back)\s+panels?\b", ""),
    (r"\b(front|back)\s+panels?\b", ""),
    (r"\bbetween\s+panels?\b", ""),
    (r"\b(both|each|the\s+other|opposite)\s+panels?\b", ""),
    (r"\bpanels?\b", ""),
    # framing leftovers that only make sense in a turnaround
    (r"with\s+image[\s-]*side\s+details\s+mirrored", ""),
    (r"\bimage[\s-]*side\s+details\s+mirrored\b", ""),
    (r"\b(occupying|takes?)\s+half\s+of\s+the\s+frame\b", ""),
    (r"\bequal\s+panel\s+widths\b", ""),
    (r"\btight\s+spacing\b", ""),
    (r"\bcompact\s+balanced\s+spacing\b", ""),
    (r"\b(seen\s+from\s+behind|rear\s+view)\b", ""),
    (r"\bthe\s+same\s+", ""),
)


def _scrub_panels(text: str) -> str:
    """Remove grid / turnaround wording while keeping every design detail."""
    import re
    out = text
    for pat, repl in _PANEL_SCRUB:
        out = re.sub(pat, repl, out, flags=re.I)
    # Tidy the debris: doubled separators, empty clauses, stray punctuation.
    out = re.sub(r"[,\s]*,[\s,]*", ", ", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\b(and|of|with)\s*(?=[,;.]|$)", "", out, flags=re.I)
    return out.strip(" ,;，；.")


def _find_cut(text: str) -> int:
    """Index where the camera/framing part starts, or -1.

    Only a late marker counts. Layout words such as "side-by-side" sit inside the
    style prefix or the character sentence, and cutting there deleted the design.
    """
    low = text.lower()
    best = -1
    for mk in _LATE_FRAME:
        i = low.find(mk)
        if i > 120 and (best < 0 or i < best):
            best = i
    return best


# A close-up must describe ONLY what the frame can see: face, skin, hair,
# makeup, neckline and head/neck jewellery. Everything below the collarbone —
# legs, shoes, skirt, waist, stance — and every multi-view layout word is
# dropped phrase by phrase. A phrase is kept only if it names a head-visible
# feature AND does not name a full-body/layout feature.
_HEAD_DROP = (
    r"\bfull[\s-]*body\b", r"\bfull frontal\b", r"\bfull body\b",
    r"\bon the (front|back|left|right) half\b", r"\bfront half\b", r"\bback half\b",
    r"\bdividers?\b", r"\bvertical axis\b", r"\brotated\b",
    r"\bmirrored\b", r"\bmirror\b", r"\bsymmetrical\b", r"\bequal height\b",
    r"\baligned\b", r"\bsame (stance|outfit|lighting)\b",
    r"\bthrough the back\b", r"\bthe matching\b", r"\bin back\b",
    r"\bstance\b", r"\bpose\b", r"\bweight even\b", r"\bspine\b",
    r"\bstature\b", r"\bframe\b", r"\bproportions?\b", r"\bleg[s]?\b",
    r"\bknees\b", r"\bcalves\b", r"\bankles\b", r"\bhips\b", r"\bhip line\b",
    r"\bwaist\b", r"\bwaistband\b", r"\bcorset\b", r"\bbodice\b",
    r"\bchest circumference\b", r"\bskirt\b", r"\bhem\b",
    r"\bpleats\b", r"\bpetticoat\b", r"\bdome\b", r"\bslit\b", r"\bthigh\b",
    r"\bsocks\b", r"\bover-the-knee\b", r"\blace tops\b", r"\bshoes\b",
    r"\bpumps\b", r"\bstiletto\b", r"\bheel\b", r"\btoes\b", r"\bsole\b",
    r"\bgarter\b", r"\bwaist chain\b", r"\barm bands\b", r"\bwrist cuffs\b",
    r"\bnape chain\b", r"\bspine chain\b",
    r"\bfabric\b", r"\bmaterial layers\b", r"\bbrocade\b", r"\bsatin\b",
    r"\borganza\b", r"\btulle\b", r"\bmesh\b", r"\bpatent leather\b",
    r"\bstitching\b", r"\bfibers\b", r"\broughness\b", r"\bmetallic\b",
    r"\blighting is identical\b", r"\bside light\b", r"\bshoulder blades\b",
)

_HEAD_KEEP = (
    # render style — a head shot uses the same medium as the source image
    r"\bphotoreal\b", r"\b3d render\b", r"\bphysically based\b",
    r"\bsubsurface\b", r"\bglobal illumination\b", r"\bray-traced\b",
    r"\boctahedral\b",
    # face
    r"\bface\b", r"\bfacial\b", r"\bforehead\b", r"\bhairline\b",
    r"\bcheekbones?\b", r"\bcheek\b", r"\bjaw\b", r"\bchin\b",
    r"\bnose\b", r"\bnostril\b", r"\bbrows?\b", r"\beyes?\b",
    r"\beyelids?\b", r"\blashes\b", r"\bcupid\b", r"\blips?\b",
    r"\bmouth\b", r"\bteeth\b", r"\bphiltrum\b", r"\bnasolabial\b",
    r"\bears?\b",
    # skin
    r"\bskin\b", r"\bpores?\b", r"\bmole\b", r"\bbirthmarks?\b",
    r"\bcomplexion\b",
    # hair
    r"\bhair\b", r"\bstrands?\b", r"\broots\b", r"\bcent(er|ered)[- ]?part(ed)?\b",
    r"\bfringe\b", r"\block\b",
    # makeup
    r"\bmakeup\b", r"\bfoundation\b", r"\bconcealer\b", r"\bcontour\b",
    r"\bhighlighter\b", r"\beyeshadow\b", r"\beyeliner\b", r"\bblush\b",
    r"\blipstick\b", r"\blip lacquer\b", r"\blenses\b", r"\btexture maps?\b",
    r"\bglamour\b",
    # head / neck accessories, neckline
    r"\bheaddress\b", r"\bcrown\b", r"\bearrings?\b", r"\bchoker\b",
    r"\bpendant\b", r"\bnecklace\b", r"\bchest chain\b", r"\bcleavage\b",
    r"\bcollar\b", r"\bneckline\b", r"\bstraps?\b", r"\bclavicle\b", r"\bneck\b",
)


# Chinese equivalents. Word-boundary regexps do not work on CJK, so these are
# plain substrings checked against the raw clause.
_HEAD_DROP_ZH = (
    "全身", "左右两半", "左半", "右半", "分割线", "横线", "并排", "齐平", "等高",
    "镜像", "同一站姿", "同一套", "绕纵轴", "两半", "正面人物", "背面可见",
    "骨架", "身高", "七头身", "头身", "胯宽", "腰臀", "乳量", "罩杯", "胸型",
    "两乳间距", "腰位", "腰很细", "细腰", "腿长", "双腿", "小腿", "脚踝",
    "手臂纤细", "腿上", "裙", "开衩", "褶", "衬裙", "袜", "鞋", "高跟", "鞋尖",
    "吊袜", "腿环", "臂环", "腕", "腰链", "脊链", "腰封", "腰带", "胸衣", "鱼骨",
    "衣身", "领口一圈", "肩带", "胸下收省", "站定时", "重心", "脊柱", "承重脚",
    "侧逆光", "轮廓光", "勾出身体", "压出腰线", "镜头为", "面料", "材质均为",
    "粗糙度", "反射", "背景为", "无缝渐变", "侧光压出", "腿部描", "身影",
    "姿态为正对", "手位", "双脚间距", "同一具身体", "转 180", "转180",
)

_HEAD_KEEP_ZH = (
    "脸", "额头", "发际线", "颧骨", "苹果肌", "法令纹", "下颌", "下巴", "侧颜",
    "鼻根", "鼻尖", "鼻翼", "鼻背", "眉", "眼", "眼裂", "眼距", "眼角", "眼皮",
    "卧蚕", "眼窝", "唇", "唇峰", "唇珠", "人中", "耳", "肤色", "瓷白", "皮肤",
    "毛孔", "色差", "油光", "纹身", "发色", "发根", "发质", "发长", "刘海",
    "蝴蝶结", "卷发", "妆容", "底妆", "修容", "高光", "眼影", "眼线", "睫毛",
    "美瞳", "腮红", "唇线", "颈圈", "颈链", "锁骨", "吊坠", "耳坠", "耳环",
    "小时面", "次表面散射", "哑光", "冷调", "螺旋卷", "双马尾",
)


def _headshot_body(text: str) -> str:
    """Keep only head-visible clauses from a full-body / multi-view prompt."""
    import re
    parts = [p.strip() for p in re.split(r"(?<=[,;，；])\s*", text) if p.strip()]
    kept = []
    for part in parts:
        low = part.lower()
        zh = any(w in part for w in _HEAD_DROP_ZH)
        en = any(re.search(p, low) for p in _HEAD_DROP)
        if zh or en:
            continue
        keep_zh = any(w in part for w in _HEAD_KEEP_ZH)
        keep_en = any(re.search(p, low) for p in _HEAD_KEEP)
        if keep_zh or keep_en:
            kept.append(part.rstrip(" ,;，；"))
    out = ", ".join(kept)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r",\s*,+", ",", out).strip(" ,;")
    return out


def _recompose_as_headshot(prompt: str, lang: str = "en") -> str | None:
    """Keep the character and the wardrobe, replace the camera.

    Two mistakes are being avoided here: cutting at the first layout word (which
    deleted the design), and deleting whole clauses that mention panels (which
    deleted the subject along with the wording). The cut is taken only at a real
    camera marker, and panel wording is scrubbed phrase by phrase.
    """
    text = (prompt or "").strip()
    if not text:
        return None

    cut = _find_cut(text)
    raw = text if cut < 0 else text[:cut].rstrip(" ,;.")
    raw = _scrub_panels(raw)

    # A close-up shows only what is above the collarbone. Filter the character
    # half down to head-visible clauses; if that removes nearly everything,
    # fall back to the scrubbed text so a short prompt is not destroyed.
    body = _headshot_body(raw)
    if len(body) < 120:
        body = raw

    if len(body) < 120:
        return None

    # The output language is a fixed rule now (see LANGUAGE_RULE), so the
    # local fallback writes the close-up caption in Chinese as well.
    head = ("大头照特写，画幅从锁骨往上：完整头部、颈部与锁骨，面部占画面主要面积，"
            "85mm 镜头，浅景深，背景干净")
    tail = ("无表情，正对镜头，头部水平，颈部自然伸展，双肩放松下沉，锁骨平展")

    return f"{head}; {body}; {tail}"


# Opening phrases that mark a lane answering with prose instead of the JSON
# contract. Checked only on text that does not begin with the object itself.
_REFUSAL_MARKERS = (
    "我不能", "我无法", "无法协助", "不会编写", "不会继续", "不能继续",
    "不能提供", "抱歉", "对不起", "很抱歉", "无法完成", "不予",
    "作为一个ai", "作为人工智能", "ai助手", "ai语言模型",
    "违反了", "违反政策", "不当内容", "敏感内容", "不合适", "不合规",
    "道德", "伦理", "政策规定", "安全策略",
    "i can't", "i cannot", "i can’t", "i won't", "i won’t",
    "i'm sorry", "i’m sorry", "sorry, i", "unable to",
    "i must refuse", "i have to decline", "cannot assist",
    "cannot provide", "not able to", "against my",
    "as an ai", "against my guidelines", "against my policy",
    "inappropriate", "unethical", "violates the",
    "无法满足", "不能帮助", "不能协助", "不会提供", "不能生成", "无法生成",
)


def _looks_like_refusal(text: str) -> bool:
    """True when the reply is prose explaining why it will not do the task.

    The contract is a single JSON object; anything that opens with conversational
    hedging and carries no JSON is a refusal wearing a 200.
    """
    if not text:
        return False
    head = text[:600].strip().lower()
    if head.startswith("{") or '"rewritten_prompt"' in head:
        return False
    return any(m in head for m in _REFUSAL_MARKERS)


def _run_lanes(system: str, user: str, model: str = "", timeout: float = 180,
               temperature: float = 0.85, max_tokens: int = 6000,
               tier: str = "normal", style_key: str = "random",
               style_zh: str = "", visual_style="none",
               composition: str = "headshot") -> dict:
    """Shared model-selection and retry loop for any single request."""
    base = ""
    key = _read_forward_key()
    probed = cached_probe()
    if probed:
        known = {m["id"]: m for m in probed}
        # An explicitly chosen model goes first, whether or not the probe has
        # seen it: the probe only samples the free lanes, so channel models
        # (ByteDance, Qwen, Spark...) always look unprobed and used to be skipped.
        ok_ids = [m["id"] for m in probed if m.get("status") == "ok"]
        rest = [m["id"] for m in probed if m["id"] != model]
        # Same three-tier order as write_prompt: cloud → Ollama → ComfyUI.
        # comfy: text_encoders drive the render GPU and were in ok_remote, so a
        # failed cloud pick could cascade into an unasked-for comfy model.
        def _is_comfy(mid: str) -> bool:
            return mid.startswith(COMFYUI_CHANNEL_PREFIX) or \
                known.get(mid, {}).get("channel") == "comfyui"

        ok_remote = [i for i in ok_ids
                     if known.get(i, {}).get("channel") != "local" and not _is_comfy(i)]
        ok_local = [i for i in ok_ids
                    if known.get(i, {}).get("channel") == "local"]
        ok_comfy = [i for i in ok_ids if _is_comfy(i)]
        candidates = (
            ([model] if model else [])
            + ok_remote
            + ok_local
            + ok_comfy
            + [i for i in rest if i not in ok_ids and not _is_comfy(i)]
        )
    else:
        known = {m["id"]: m for m in list_models(base=base, key=key)}
        candidates = list(known)
        if model:
            candidates = [model] + [c for c in candidates if c != model]

    if not candidates:
        raise RuntimeError("网关没有返回任何模型")

    last: Exception | None = None
    tried = 0
    for mid in candidates:
        is_local = known.get(mid, {}).get("channel") == "local"
        if tried >= 18 and not is_local:
            break
        tried += 1
        gw = (known.get(mid, {}) or {}).get("gateway") or base or OFM_BASE
        try:
            return _call_once(gw, key, mid, system, user,
                              timeout, temperature, max_tokens,
                              tier, style_key, style_zh, visual_style, composition)
        except _RateLimited as e:
            last = e
            _LOG.warn("写词网关限流: %s" % gw)
            continue
        except _Refused as e:
            last = e
            _LOG.warn("写词网关拒绝: %s" % gw)
            continue
        except Exception as e:
            last = e
            _LOG.warn("写词网关异常: %s model=%s -> %s" % (gw, mid, str(e)[:120]))
            continue
    if last:
        _LOG.log_exc("写词所有通道失败，最后错误来自 %s" % gw, last)
    raise last or RuntimeError("所有通道都失败了")


# Layout vocabulary that makes an image model draw a grid or a turnaround sheet.
# Only checked for the multi-view compositions.
_LAYOUT_WORDS = (
    "four panel", "four-panel", "quad grid", "2x2", "character sheet",
    "turnaround", "turnaround sheet", "model sheet", "contact sheet",
    "diptych", "triptych", "grid of", "four views", "multiple views",
)


def _has_layout_words(text: str) -> bool:
    low = (text or "").lower()
    return any(w in low for w in _LAYOUT_WORDS)


def write_prompt(
    brief: str,
    tier: str = "normal",
    style: str = "random",
    composition: str = "full_body",
    extra_system: str = "",
    model: str = "",
    lang: str = "en",
    visual_style="none",
    with_action: bool = False,
    detail: str = "normal",
    char_style="none",
    base: str = "",
    key: str = "",
    timeout: float = 180,
    temperature: float = 0.85,
    max_tokens: int = 6000,
    enabled_blocks=None,
    think="off") -> dict:
    """One draw. Falls through the model list when a lane answers 429.

    `think` is the 思考强度 level: "off" (default) / "on" / "low" /
    "medium" / "high" — the lanes map it onto whatever knob they expose.
    """
    base = base or ""
    key = key or _read_forward_key()
    _WRITE_CANCEL.clear()

    asm = build_prompt(brief, tier, style, composition, lang,
                       visual_style, with_action, detail, extra_system,
                       char_style, enabled_blocks)
    system, user = asm.system, asm.user
    style_key, _b, _i = resolve_style(style)
    style_zh = style_label(style) if visual_style else _TAX.resolve(style_key)[0]

    # Each model remembers which gateway serves it: the EAC router exposes the
    # account channels that the plain forward listener does not.
    probed = cached_probe()
    if probed:
        known = {m["id"]: m for m in probed}
        ok_ids = [m["id"] for m in probed if m.get("status") == "ok"]
        rest = [m["id"] for m in probed if m["id"] != model]
        # The local models are the LAST resort, not the first: they are slow
        # and their output is weaker than a cloud model's, so a working
        # cloud lane always wins. A model the user picked by hand still goes
        # first, local or not.
        def _is_local(mid: str) -> bool:
            return known.get(mid, {}).get("channel") == "local"

        def _is_comfy(mid: str) -> bool:
            return mid.startswith(COMFYUI_CHANNEL_PREFIX) or \
                known.get(mid, {}).get("channel") == "comfyui"

        # Three tiers, newest first: cloud (no GPU) → Ollama local → ComfyUI
        # text_encoder (drives the render GPU). ComfyUI was in ok_remote before,
        # so a failed cloud pick cascaded into an unasked-for comfy: model that
        # then occupied the render GPU. Keep it strictly last, and rely on the
        # strict_comfy single-lane rule below when the user picked one by hand.
        ok_remote = [i for i in ok_ids if not _is_local(i) and not _is_comfy(i)]
        ok_local = [i for i in ok_ids if _is_local(i)]
        ok_comfy = [i for i in ok_ids if _is_comfy(i)]
        candidates = (
            ([model] if model else [])
            + ok_remote
            + ok_local
            + ok_comfy
            + [i for i in rest if i not in ok_ids and not _is_comfy(i)]
        )
    else:
        known = {m["id"]: m for m in list_models(base=base, key=key)}
        candidates = list(known)
        if model:
            candidates = [model] + [c for c in candidates if c != model]

    if not candidates:
        raise RuntimeError("网关没有返回任何模型")

    # A comfyui: model the user picked is a STRICT single-lane decision.
    # Cascading to a cloud lane after a "too short" verdict is what turned a
    # 25s local write into a 1-3 minute wait: int8 4B writes compact designs
    # (real outputs 651/724 chars) that fell under the cloud-tuned 700-char
    # floor, so the ladder tried every cloud candidate at 30-60s each — and
    # the user got a slow CLOUD answer instead of the local int8 one they
    # picked. Honour the pick: if the local model answered, accept it; if it
    # truly failed, fall through to the local template, never to a cloud lane.
    strict_comfy = bool(model and model.startswith(COMFYUI_CHANNEL_PREFIX))
    if strict_comfy:
        candidates = [model]

    last: Exception | None = None
    tried = 0
    for mid in candidates:
        if _WRITE_CANCEL.is_set():
            raise RuntimeError("写词已被用户中断")
        # The local models are always worth a try, even when the attempt
        # budget is nearly spent: they are the only lane that answers
        # without an account, and the budget is otherwise eaten by dead
        # cloud models.
        is_local = known.get(mid, {}).get("channel") == "local"
        if tried >= 12 and not is_local:
            break
        tried += 1
        gw = (known.get(mid, {}) or {}).get("gateway") or base or OFM_BASE
        try:
            out = _call_once(gw, key, mid, system, user,
                             timeout, temperature, max_tokens, tier, style_key, style_zh,
                             visual_style, composition, think=think)
            # Measure the whole design, not just the composition half: the
            # close-up segment is part of it.
            design_chars = out.get("design_chars") or len(out.get("prompt", ""))
            # The 700-char floor was tuned for verbose cloud models. A local
            # int8 4B writes tight but complete designs (measured 651–724
            # chars); judging them by the cloud bar is what bounced a good
            # answer into the slow cloud ladder. Give comfyui its own, lower
            # floor so a real answer is accepted on the first, fast call.
            floor = MIN_PROMPT_CHARS_COMFY.get(tier, 300) if strict_comfy \
                else MIN_PROMPT_CHARS.get(tier, 400)
            if design_chars >= floor:
                # Multi-view compositions must not come back describing a grid or
                # a character sheet: the image model draws exactly what it reads.
                # Under a strict single-lane pick there is no next candidate —
                # retrying only loops back to this same model — so accept it.
                if composition in ("front_back", "headshot_plus_front_back") and \
                        _has_layout_words(out.get("prompt", "")) and not strict_comfy:
                    last = RuntimeError(f"{mid} 输出含分格/转面词，重试")
                    continue
                return out
            last = RuntimeError(f"{mid} 输出过短（{len(out.get('prompt',''))} 字）")
            continue
        except _RateLimited as e:
            last = e
            continue
        except Exception as e:
            last = e
            # An interrupted/cancelled ComfyUI write means the user pressed
            # 中断: stop the ladder entirely instead of feeding it the next
            # model.
            msg = str(e).lower()
            if "中断" in str(e) or "interrupted" in msg or "canceled" in msg \
                    or "cancelled" in msg:
                _WRITE_CANCEL.set()
            continue

    # Every lane is spent or throttled. Rather than hand back nothing, build the
    # prompt from the taxonomy directly: the same category anchor, brief and
    # garment list, assembled without a model. Flagged so the UI can say so.
    fallback = _assemble_fallback(brief, tier, style, composition, lang, style_key, style_zh, visual_style)
    fallback["error"] = f"模型全部不可用（{tried} 个都失败：{last}），已用本地模板兜底"
    return fallback


def _assemble_fallback(brief, tier, style, composition, lang, style_key, style_zh,
                       visual_style="none") -> dict:
    """Compose a usable prompt from the taxonomy when no model answers."""
    # `style` may be a list (multi-pick), so route through the multi resolver.
    if isinstance(style, (list, tuple)):
        labels = [k for k in style if k]
        if labels:
            _l, style_brief, items = _TAX.resolve_multi(labels)
        else:
            _l, style_brief, items = _TAX.resolve("random")
    else:
        _l, style_brief, items = _TAX.resolve(style)
    comp = COMPOSITION_MODES.get(composition, COMPOSITION_MODES["full_body"])
    vphrase = style_phrase(visual_style)
    style_clause = f" {vphrase}。" if vphrase else ""
    # The output language is a fixed rule now (see LANGUAGE_RULE), so the
    # local fallback writes its template in Chinese as well — a Chinese
    # fallback under an English rule would be the odd one out.
    prompt = (
        f"{brief.strip()}。{style_brief}。{style_clause}本服装可选款式：{items}。"
        f"从中选一套完整造型，逐项写清结构：领型、袖型、腰线高度、裙长、开衩位置、"
        f"材质与表面特征、颜色色号、每一件五金件、鞋与饰品的位置材质。"
        f"面部写清脸型、额头、颧骨、下颌角、下巴、眉形、眼型与眼距、鼻梁鼻翼、唇厚度与唇峰；"
        f"发型写清发色发质长度与固定方式；妆容写清底妆、眼影范围、眼线、睫毛、唇色。"
        f"体型写清身高、骨架、肩宽、腰臀比、四肢比例。构图：{comp}"
        f"背景：无缝中性浅灰棚拍，无道具、无环境。光：中性正面主光加柔和 3/4 补光。"
    )
    return {
        "prompt": prompt,
        # The local template has no -XXX- segment to cut out, but the field
        # must exist: the card reads it to decide whether to offer the
        # 构图版/大头版 switch.
        "prompt_headshot": "",
        "design_chars": len(prompt),
        "raw": "",
        "parsed": None,
        "notes": "本地模板兜底（模型不可用）",
        "wh_ratio": "2:3",
        "model": "local-template",
        "tier": tier,
        "tier_zh": D.TIER_META[tier]["zh"],
        "style": style_key,
        "style_zh": style_zh,
        "usage": {},
        "fallback": True,
    }


# A draw shorter than this reads as a fragment, not a design.
MIN_PROMPT_CHARS = {
    "normal": 700,
    "edgy": 700,
    "nude": 800,
    "explicit": 900,
}

# A local int8 4B model writes far more compactly than the cloud lanes the
# 700-char floor was tuned for. Real outputs measured 651–724 chars and were
# complete, well-formed designs. Keep a floor that still rejects genuine
# fragments but does not bounce a good local answer into the slow cloud ladder.
MIN_PROMPT_CHARS_COMFY = {
    "normal": 300,
    "edgy": 300,
    "nude": 350,
    "explicit": 400,
}


# Set by the UI's 中断 button (POST /api/cancel). The write ladder checks it
# before every attempt, so a cancelled run stops instead of crawling through
# the rest of the model list — each stop on that ladder is another queued
# ComfyUI job the user would have to cancel again.
_WRITE_CANCEL = threading.Event()


def cancel_write() -> None:
    """Ask any in-flight write_prompt ladder to stop at its next checkpoint."""
    _WRITE_CANCEL.set()


# ---------------------------------------------------------------- thinking effort
# Default thinking effort for every call. "low" keeps a reasoning model from
# spending its budget planning instead of answering; when a model rejects that
# value we fall back to switching thinking off entirely.
DEFAULT_EFFORT = "low"

# How each family spells "off". The OpenAI-style effort knob takes "none";
# Anthropic-style endpoints use a reasoning object.
_OFF_AS_EFFORT = {"reasoning_effort": "none"}
_OFF_AS_OBJECT = {"reasoning": {"enabled": False}}


def _effort_patch(model: str, effort: str = DEFAULT_EFFORT) -> dict:
    """The reasoning field to merge into the payload for this model."""
    if not effort:
        return {}
    return {"reasoning_effort": effort}


def _off_patch(model: str) -> dict:
    """How to disable thinking on this model."""
    mid = (model or "").lower()
    # Models served through the Anthropic-shaped wire want the object form.
    if "/claude" in mid or mid.startswith("claude"):
        return dict(_OFF_AS_OBJECT)
    return dict(_OFF_AS_EFFORT)


def _local_gateway(base: str) -> bool:
    """Is this the local Ollama server?"""
    return (base or "").rstrip("/") == OLLAMA_BASE.rstrip("/")


# The ladder each lane exposes for the UI's 思考强度 switch. The levels are
# probed from the backend per model — not hard-coded — so a node/ server that
# grows finer-grained levels is picked up automatically.
_THINK_CLOUD_LADDER = ["off", "low", "medium", "high"]
_THINK_LEVELS_CACHE: dict = {"at": 0.0, "data": {}}


def _think_levels_comfyui() -> list:
    """What TextGenerateV2 exposes right now: BOOLEAN -> off/on, combo -> its
    options. Read straight from /object_info so a node update is followed."""
    try:
        req = urllib.request.Request(
            f"{COMFYUI_BASE.rstrip('/')}/object_info/TextGenerateV2")
        with urllib.request.urlopen(req, timeout=10) as r:
            schema = json.loads(r.read().decode("utf-8"))["TextGenerateV2"]
        arr = (schema.get("input", {}).get("optional") or {}).get("thinking")
        if isinstance(arr, list) and arr:
            if arr[0] == "BOOLEAN":
                return ["off", "on"]
            if isinstance(arr[0], list):  # COMBO: options live in arr[0]
                opts = [str(o).lower() for o in arr[0]]
                ladder = [o for o in ("off", "low", "medium", "high") if o in opts]
                if ladder:
                    return ladder
    except Exception:
        pass
    return ["off", "on"]


def _think_levels_ollama(model: str) -> list:
    """Ollama's /api/show capabilities. Models without the thinking
    capability only get off; thinking models get the string-level ladder
    (0.9+ accepts low/medium/high — a level the chat template rejects falls
    back to on/off at call time)."""
    try:
        body = json.dumps({"model": model}).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_BASE.rstrip('/')}/api/show", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            caps = json.loads(r.read().decode("utf-8")).get("capabilities") or []
        if "thinking" in caps:
            return ["off", "low", "medium", "high"]
        return ["off"]
    except Exception:
        return ["off", "on"]


def think_levels(model: str, base: str = "") -> list:
    """The thinking levels the UI offers for this model (probe per lane)."""
    m = (model or "").strip()
    if not m:
        return ["off", "on"]
    if m.startswith(COMFYUI_CHANNEL_PREFIX):
        return _think_levels_comfyui()
    # Ollama models carry channel "local" in the probe cache; anything else
    # is a cloud lane speaking the OpenAI-style effort ladder.
    try:
        probed = cached_probe()
        if probed:
            ch = {x["id"]: x for x in probed}.get(m, {}).get("channel")
            if ch == "local":
                return _think_levels_ollama(m)
    except Exception:
        pass
    return list(_THINK_CLOUD_LADDER)


# ----------------------------------------------------------- VRAM management
# The local box has 8 GB of VRAM and ComfyUI usually owns most of it. There is
# no warmth strategy: every Ollama call carries keep_alive=0, so the model
# unloads the moment its generation finishes. ollama_unload() remains as the
# manual button / render-entry safety net for anything that slipped through.


def ollama_unload(model: str = "") -> dict:
    """Unload Ollama model(s) from VRAM; empty name = every loaded model."""
    base = OLLAMA_BASE.rstrip("/")
    if model:
        targets = [model]
    else:
        try:
            with urllib.request.urlopen(f"{base}/api/ps", timeout=10) as r:
                ps = json.loads(r.read().decode("utf-8"))
            targets = [m.get("name", "") for m in ps.get("models", []) if m.get("name")]
        except Exception as e:
            return {"ok": False, "error": str(e), "unloaded": []}
    unloaded: list[str] = []
    for name in targets:
        try:
            body = json.dumps({"model": name, "keep_alive": 0,
                               "prompt": "", "stream": False}).encode("utf-8")
            req = urllib.request.Request(f"{base}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                r.read()
            unloaded.append(name)
        except Exception as e:
            return {"ok": False, "error": f"{name}: {e}", "unloaded": unloaded}
    return {"ok": True, "unloaded": unloaded}


def _is_context_error(detail: str) -> bool:
    """Does this error say the prompt did not fit the context window?"""
    low = (detail or "").lower()
    return ("exceed" in low and "context" in low) or "context size" in low \
        or "context_length" in low or "too many tokens"


def _ollama_body(model: str, messages: list, temperature: float = 0.85,
                 max_tokens: int = 6000, num_ctx: int = 0,
                 think="off"):
    """The request body for Ollama's NATIVE /api/chat endpoint.

    Two fields matter here and neither exists on the OpenAI-shaped route:

    `options.num_ctx` — Ollama serves a 4096-token context by default and
    this tool's system prompt alone is ~5400 characters, so the request is
    refused outright ("exceeds the available context size") before the model
    ever sees it. The installed models support far more than the default.

    `think` — the installed qwen3 models think before they answer and would
    spend the whole token budget on reasoning, leaving an empty answer, so
    "off" is the default. Ollama 0.9+ also accepts the string levels
    "low"/"medium"/"high" for models whose chat template supports them; a
    level the model rejects is caught upstream and downgraded.

    `keep_alive: 0` — no warmth. 8 GB VRAM shared with ComfyUI: the model
    unloads the moment this generation finishes, so two models can never sit
    resident at once and the render lane never finds VRAM missing.
    """
    if think in (None, "", "off", False) or think == "off":
        think_val = False
    elif think in ("on", True):
        think_val = True
    else:
        think_val = str(think)  # low / medium / high — passed natively
    return {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think_val,
        "keep_alive": 0,
        "options": {
            "num_ctx": int(num_ctx or OLLAMA_NUM_CTX),
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }


def _ollama_chat(base: str, model: str, system: str, user: str, timeout: float,
                 temperature: float = 0.85, max_tokens: int = 6000,
                 num_ctx: int = 0, think: str = "off") -> dict:
    """Call the local Ollama server and answer in the OpenAI shape.

    Ollama's /v1/chat/completions is a thin shim that ignores
    `options.num_ctx`, so the long system prompt does not fit in the
    server's default window and the call is rejected. The native
    /api/chat endpoint honours it, so the local lane goes there and the
    reply is translated back into the shape the rest of this module
    already speaks: choices[0].message.content plus a usage block.
    """
    body = _ollama_body(
        model,
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        temperature, max_tokens, num_ctx, think=think,
    )
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        # A string level (low/medium/high) the chat template does not
        # understand: walk down the ladder instead of losing the call.
        if e.code in (400, 422, 500) and str(think) in ("low", "medium", "high"):
            ladder = {"low": "on", "medium": "low", "high": "medium"}
            return _ollama_chat(base, model, system, user, timeout,
                                temperature, max_tokens, num_ctx,
                                think=ladder[str(think)])
        raise

    # The native endpoint answers with one JSON object, but it may also
    # stream NDJSON; the last complete line is the finished turn.
    data = None
    for line in reversed((raw or "").strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(data, dict):
        raise RuntimeError(f"{model} 本地返回无法解析")

    msg = data.get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str):
        content = ""
    # A thinking turn keeps the prose in a sibling field. With think:false
    # that should not happen, but if the model ignores the switch the prose
    # is still there and worth using.
    if not content:
        content = (msg.get("thinking") or "").strip()

    prompt_tokens = data.get("prompt_eval_count") or 0
    completion_tokens = data.get("eval_count") or 0
    return {
        "model": data.get("model") or model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": data.get("done_reason") or "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


# ---------------------------------------------- ComfyUI text_encoders lane
# ComfyUI's models/text_encoders folder holds safetensors text encoders that
# the core CLIPLoader node can mount (e.g. "qwen3.5 4B int8无审查.safetensors").
# The core TextGenerateV2 node turns such a CLIP into a chat LLM, so a write
# request is submitted as a tiny workflow: CLIPLoader -> TextGenerateV2 (the
# design system text wired into system_prompt, the user brief into prompt) ->
# a core SaveText node to land the answer — then polled from /history.
#
# The node runs in ComfyUI's own queue, so these writes queue behind (and
# ahead of) renders on the same lane. After each write the lane frees VRAM
# (POST /free) when the queue is idle, so the encoder does not keep sitting in
# the 8 GB card — the same discipline the render entry points enforce for
# Ollama.
COMFYUI_BASE = os.environ.get("COMFYUI_BASE", "http://127.0.0.1:8188")
COMFYUI_CHANNEL_PREFIX = "comfyui:"
COMFYUI_CLIP_TYPE = os.environ.get("COMFYUI_CLIP_TYPE", "qwen_image")
COMFYUI_GEN_NODE = "TextGenerateV2"
# A complete design + -XXX- close-up is ~1000 chars (~1500 tokens for CJK).
# The old 6144 ceiling let a looping model run for 190s producing 7800 chars
# of repeated text. 2400 leaves comfortable headroom but bounds a runaway to
# ~60s; pair this with the prompt fix and _dedupe_repeats() post-filter.
COMFYUI_GEN_MAX_TOKENS = int(os.environ.get("COMFYUI_GEN_MAX_TOKENS", "2400"))
_comfyui_clip_cache: dict = {"at": 0.0, "names": []}
_COMFYUI_CLIP_LOCK = threading.Lock()

# ComfyUI text_encoders come from /object_info/CLIPLoader. That call is local
# but still a round trip, and it used to be appended only AFTER every remote
# gateway answered — which is why the comfyui lane appeared late ("探测半天").
# Mirror discovered names to disk so a fresh page paints the comfyui lane
# instantly (zero network) while the real probe runs in the background.
_COMFY_MODELS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "comfyui_models.json")


def _load_comfyui_names_file() -> list[str]:
    try:
        with open(_COMFY_MODELS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        names = data.get("names") if isinstance(data, dict) else data
        return [n for n in names if isinstance(n, str)] if isinstance(names, list) else []
    except Exception:
        return []


def _save_comfyui_names_file(names: list[str]) -> None:
    try:
        os.makedirs(os.path.dirname(_COMFY_MODELS_FILE), exist_ok=True)
        tmp = _COMFY_MODELS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"names": names}, fh, ensure_ascii=False)
        os.replace(tmp, _COMFY_MODELS_FILE)
    except Exception:
        pass


def comfyui_models_cached() -> list[dict]:
    """ComfyUI lane from the on-disk mirror — instant, no network, always ok."""
    return [{
        "id": COMFYUI_CHANNEL_PREFIX + name,
        "name": name,
        "channel": "comfyui",
        "source": "ComfyUI text_encoders（本地 int8 safetensors）",
        "gateway": COMFYUI_BASE,
        "context": None,
        "free": False,
        "status": "ok",
        "ms": 0,
    } for name in _load_comfyui_names_file()]


def _comfyui_clip_names(timeout: float = 20) -> list:
    """The models CLIPLoader can mount = ComfyUI's models/text_encoders.

    Cached briefly so /api/models does not hammer ComfyUI on every refresh.
    """
    now = time.time()
    with _COMFYUI_CLIP_LOCK:
        if _comfyui_clip_cache["names"] and now - _comfyui_clip_cache["at"] < 10:
            return _comfyui_clip_cache["names"]
    req = urllib.request.Request(
        f"{COMFYUI_BASE.rstrip('/')}/object_info/CLIPLoader")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    arr = data["CLIPLoader"]["input"]["required"]["clip_name"]
    names = arr[0] if arr and isinstance(arr[0], list) else []
    with _COMFYUI_CLIP_LOCK:
        _comfyui_clip_cache["at"] = now
        _comfyui_clip_cache["names"] = names
    if names:
        _save_comfyui_names_file(names)
    return names


def prewarm_comfyui_models(timeout: float = 20):
    """后台预热：启动时刷新 ComfyUI text_encoders 缓存到磁盘。

    不阻塞启动；有缓存时页面已能秒显，此函数只负责让缓存跟上 ComfyUI 的
    最新模型列表。失败静默（ComfyUI 可能还没开），下次探测会再试。
    """
    def _do():
        try:
            names = _comfyui_clip_names(timeout)
            _LOG.info("模型预热完成: %d 个 comfyui text_encoders" % len(names))
        except Exception as e:
            _LOG.warn("模型预热跳过（ComfyUI 未就绪?）: %s" % str(e)[:120])
    threading.Thread(target=_do, daemon=True).start()


def comfyui_local_models(timeout: float = 20) -> list[dict]:
    """The text_encoders models ComfyUI can run writes on, as a model lane."""
    try:
        names = _comfyui_clip_names(timeout)
    except Exception:
        return []
    return [{
        "id": COMFYUI_CHANNEL_PREFIX + name,
        "name": name,
        "channel": "comfyui",
        "source": "ComfyUI text_encoders（本地 int8 safetensors）",
        "gateway": COMFYUI_BASE,
        "context": None,
        "free": False,
        "status": "ok",
        "ms": 0,
    } for name in names]


def comfyui_free_vram(timeout: float = 30) -> bool:
    """Ask ComfyUI to unload every model it holds (best effort).

    Only fires when the ComfyUI queue is idle — yanking models out from under
    a running render would break it, so a busy queue is left alone.
    """
    try:
        with urllib.request.urlopen(f"{COMFYUI_BASE.rstrip('/')}/queue",
                                    timeout=timeout) as r:
            q = json.loads(r.read().decode("utf-8"))
        if q.get("queue_running") or q.get("queue_pending"):
            return False
        body = json.dumps({"unload_models": True, "free_memory": True}).encode("utf-8")
        req = urllib.request.Request(
            f"{COMFYUI_BASE.rstrip('/')}/free", data=body,
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=timeout).read()
        return True
    except Exception:
        return False


@_CFG.serialize_gpu
def _comfyui_local_chat(model: str, system: str, user: str,
                        timeout: float, think: str = "off") -> dict:
    """Run one write through ComfyUI's CLIPLoader + TextGenerateV2 lane.

    Serialized against image renders: this drives the same ComfyUI/GPU, so a
    text model must not be swapped in while a render is loading an image model.

    Returns the OpenAI shape the rest of the module speaks. The answer comes
    from the SaveText node's ui payload in /history; the on-disk file is the
    fallback for the rare case the ui payload is missing.
    """
    base = COMFYUI_BASE.rstrip("/")
    ts = int(time.time() * 1000)
    prefix = f"dress-gacha/dsg_{ts}"
    graph = {
        "1": {
            "class_type": "PrimitiveStringMultiline",
            "inputs": {"value": system},
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {"clip_name": model, "type": COMFYUI_CLIP_TYPE},
        },
        "3": {
            "class_type": COMFYUI_GEN_NODE,
            "inputs": {
                "clip": ["2", 0],
                "prompt": user,
                # system_prompt is a forceInput: the design system text must
                # be wired in, and use_default_template stays True or the
                # wired prompt is ignored by the chat template.
                "system_prompt": ["1", 0],
                "max_length": COMFYUI_GEN_MAX_TOKENS,
                # Dynamic combo flattened to its key: "off" = greedy decode,
                # no sampling sub-inputs. Deterministic output keeps the JSON
                # contract stable.
                "sampling_mode": "off",
                # TextGenerateV2 only exposes a boolean: off by default (a
                # thinking turn eats into max_length and is much slower); the
                # UI's 思考强度 levels all map to True for this node.
                "thinking": str(think) != "off",
                "use_default_template": True,
            },
        },
        "4": {
            "class_type": "SaveText",
            "inputs": {
                "text": ["3", 0],
                "filename_prefix": prefix,
                "format": "txt",
            },
        },
    }
    # Free any model cached by a previous render/write before this one loads
    # its text encoder — the user asked for a clean GPU/RAM cache each time.
    comfyui_free_vram()
    body = json.dumps({"prompt": graph, "client_id": "dress-gacha"}).encode("utf-8")
    req = urllib.request.Request(f"{base}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        ack = json.loads(r.read().decode("utf-8"))
    prompt_id = ack.get("prompt_id") or ""
    if not prompt_id:
        raise RuntimeError(f"ComfyUI 没有受理写词任务：{str(ack)[:200]}")

    try:
        deadline = time.time() + max(timeout, 900)
        history: dict = {}
        while time.time() < deadline:
            time.sleep(2.0)
            if _WRITE_CANCEL.is_set():
                # The user pressed 中断: pull this prompt out of the ComfyUI
                # queue so it stops occupying the lane.
                try:
                    body = json.dumps({"delete": [prompt_id]}).encode("utf-8")
                    req = urllib.request.Request(
                        f"{base}/api/queue", data=body,
                        headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req, timeout=15).read()
                except Exception:
                    pass
                raise RuntimeError("写词已被用户中断")
            with urllib.request.urlopen(f"{base}/history/{prompt_id}",
                                        timeout=30) as r:
                hist = json.loads(r.read().decode("utf-8"))
            entry = hist.get(prompt_id)
            if not entry:
                continue
            status = entry.get("status") or {}
            if status.get("status_str") == "error" or status.get("completed") is True:
                history = entry
                break
        if not history:
            raise TimeoutError("ComfyUI 本地写词超时（任务可能仍在队列中）")
        status = history.get("status") or {}
        if status.get("status_str") == "error":
            msgs = [m.get("message", "") for m in (status.get("messages") or [])]
            raise RuntimeError("ComfyUI 本地写词失败：" + " | ".join(
                str(m)[:200] for m in msgs if m)[-600:])

        outputs = history.get("outputs") or {}
        save_out = outputs.get("4") or {}
        text_parts = save_out.get("text") or []
        text = "\n".join(str(t) for t in text_parts).strip()
        if not text:
            # Fallback: read the file SaveText landed in the output directory.
            out_dir = _comfyui_output_dir()
            path = os.path.join(out_dir, "dress-gacha", f"dsg_{ts}_00001.txt")
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    text = fh.read().strip()
            except OSError as e:
                raise RuntimeError(f"ComfyUI 写词结果为空，且落盘文件读取失败：{e}")
    finally:
        # Free VRAM unless another job is already waiting on the lane.
        comfyui_free_vram()
    return {
        "model": COMFYUI_CHANNEL_PREFIX + model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {},
    }


def _comfyui_output_dir() -> str:
    """ComfyUI's output directory (env override for non-standard installs)."""
    return os.environ.get("COMFYUI_OUTPUT_DIR", _CFG.COMFY_OUTPUT_ROOT)



def _call_once(base, key, model, system, user, timeout, temperature, max_tokens,
               tier, style_key, style_zh,
               visual_style="none", composition="full_body",
               think: str = "off") -> dict:
    # The ComfyUI text_encoders lane speaks ComfyUI's queue protocol, not
    is_comfy = model.startswith(COMFYUI_CHANNEL_PREFIX)
    if is_comfy:
        # The ComfyUI lane returns the raw chat shape; let it fall
        # through to the shared content parsing below so the result
        # carries prompt/design_chars like every other lane.
        resp = _comfyui_local_chat(model[len(COMFYUI_CHANNEL_PREFIX):],
                                   system, user, timeout, think=think)
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        # Thinking knob, per the UI's 思考强度 level: "off" asks the cloud lane
        # for low-effort thinking (with a retry below that switches it off
        # entirely if the model refuses); "on" hands the model its own default;
        # low/medium/high are forwarded as the effort itself. The local Ollama
        # server ignores "low" and keeps thinking until the token budget runs
        # out, so any non-off level goes through the native body instead.
        local = _local_gateway(base)
        if not local:
            if think in ("off", "", None, False):
                payload.update(_effort_patch(model))
            elif str(think) in ("low", "medium", "high"):
                payload.update(_effort_patch(model, effort=str(think)))
            # "on": no patch — the model's own default.

        # A local model runs on this machine's own CPU/GPU: the first call has to
        # read the GGUF off disk and load it, and the answer is generated token by
        # token. A 180s budget — fine for a cloud lane — is not enough, and the
        # call would fail with a timeout instead of a slow answer.
        local_timeout = max(timeout, OLLAMA_TIMEOUT) if local else timeout

        def post(payload: dict):
            if local:
                num_ctx = (payload.get("options") or {}).get("num_ctx", OLLAMA_NUM_CTX)
                return _ollama_chat(base, model, system, user, local_timeout,
                                    temperature, max_tokens, num_ctx, think=think)
            req = urllib.request.Request(
                f"{base}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers=_auth_headers(base, key),
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))

        try:
            resp = post(payload)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            if e.code == 429:
                raise _RateLimited(f"{model} 额度用尽") from e
            # The prompt is longer than the window the server is willing to give.
            # Widen it and try again rather than losing the lane: the models
            # support far more than the default.
            if e.code in (400, 413, 422) and _is_context_error(detail):
                widened = dict(payload)
                opts = dict(widened.get("options") or {})
                opts["num_ctx"] = max(OLLAMA_NUM_CTX * 2, 65536)
                widened["options"] = opts
                try:
                    resp = post(widened)
                except urllib.error.HTTPError as e2:
                    d2 = ""
                    try:
                        d2 = e2.read().decode("utf-8", "replace")[:300]
                    except Exception:
                        pass
                    if e2.code == 429:
                        raise _RateLimited(f"{model} 额度用尽") from e2
                    raise RuntimeError(f"{model} HTTP {e2.code}: {d2 or e2.reason}") from e2
                except urllib.error.URLError as e2:
                    raise RuntimeError(f"{model} 不可达：{e2.reason}") from e2
            # The model may not accept reasoning_effort at all, or not the value
            # "low". Retry once with thinking switched off rather than failing the
            # lane: a low default is a preference, not a requirement.
            elif e.code in (400, 404, 422) and "reasoning" in (detail or "").lower():
                fallback = dict(payload)
                fallback.pop("reasoning_effort", None)
                fallback.pop("reasoning", None)
                fallback.update(_off_patch(model))
                try:
                    resp = post(fallback)
                except urllib.error.HTTPError as e2:
                    d2 = ""
                    try:
                        d2 = e2.read().decode("utf-8", "replace")[:300]
                    except Exception:
                        pass
                    if e2.code == 429:
                        raise _RateLimited(f"{model} 额度用尽") from e2
                    raise RuntimeError(f"{model} HTTP {e2.code}: {d2 or e2.reason}") from e2
                except urllib.error.URLError as e2:
                    raise RuntimeError(f"{model} 不可达：{e2.reason}") from e2
            else:
                raise RuntimeError(f"{model} HTTP {e.code}: {detail or e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"{model} 不可达：{e.reason}") from e

    choice = (resp.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content = msg.get("content")
    # Reasoning lanes can answer with content null and the prose in a sibling
    # field; a truncated turn can also arrive with no content at all.
    if not content:
        for alt in ("reasoning_content", "reasoning", "text"):
            alt_v = msg.get(alt) or choice.get(alt)
            if alt_v:
                content = alt_v
                break
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") for p in content if isinstance(p, dict)
        )
    if not isinstance(content, str):
        content = ""
    # A lane that hits its token ceiling mid-JSON still carries usable prose in
    # the part it wrote. Keep it and let the salvage path pull the field out;
    # only a genuinely empty turn is a miss.
    if not content.strip():
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        if reasoning.strip():
            raise RuntimeError(
                f"{model} 只产出了思考内容没有正文（finish_reason={choice.get('finish_reason')}）"
            )
        raise RuntimeError(
            f"{model} 未产出正文（finish_reason={choice.get('finish_reason')}）"
        )

    parsed = _extract_json(content)
    # A refusal has no rewritten_prompt; without this check the prose fallback
    # below quietly became the "prompt" and the caller never retried.
    if _looks_like_refusal(content) and not (parsed or {}).get("rewritten_prompt"):
        raise _Refused(content[:160])

    # Truncated reasoning: no parsed prompt, no salvageable field, and the text
    # reads like the model narrating its plan rather than a prompt.
    _salv = _salvage_prompt(content)
    if not (parsed or {}).get("rewritten_prompt") and not _salv:
        _plan = ("我需要", "我要", "让我", "首先", "开发者", "输出契约",
                 "严格按", "用户给", "要求输出", "i need to", "i should",
                 "let me", "the user wants")
        if any(t in content[:400] for t in _plan):
            raise _Refused("truncated reasoning: " + content[:120])
        if len(content.strip()) < 120:      # far too short to be a prompt
            raise _Refused("reply too short: " + content[:80])

    prompt = (parsed or {}).get("rewritten_prompt") or _salvage_prompt(content) or content.strip()
    # Local 4B models can loop on the format example and repeat one clause
    # dozens of times until the token ceiling (seen: 7800 chars / 190s from a
    # design that should be ~600 chars / 13s). Cut the loop before measuring
    # length or splitting, so a runaway answer never dominates the result.
    prompt = _dedupe_repeats(prompt)
    notes = (parsed or {}).get("design_notes") or _salvage_field(content, "design_notes") or ""
    ratio = (parsed or {}).get("wh_ratio") or _salvage_field(content, "wh_ratio") or ""

    # The close-up companion prompt, when the model supplied one. A headshot
    # composition has no companion; a miss here is not an error.
    head = (
        (parsed or {}).get("rewritten_prompt_headshot")
        or _salvage_field(content, "rewritten_prompt_headshot")
        or ""
    )
    if isinstance(head, str):
        head = head.strip()
    else:
        head = ""

    # Enforce the style prefix rather than trusting the model to comply: the
    # downstream image model weights the opening words most heavily.
    prompt = _ensure_style_prefix(prompt, visual_style)

    # The system message asks for the close-up as a -XXX- segment inside the
    # main prompt. When the model followed that contract, split it out here:
    # the composition version is everything except the segment, the headshot
    # version is the segment with its hyphens. This is the automatic path —
    # no second API call, no manual button needed. If the model instead used
    # the old two-field contract, `head` above already holds it.
    #
    # The length of the WHOLE design is measured before the cut: the segment
    # is part of the design, and judging the composition half alone made a
    # perfectly good design look truncated and sent it round the model list
    # again.
    design_chars = len(prompt)
    if not head:
        prompt, head = split_headshot(prompt)
    if head:
        head = _ensure_style_prefix(head, visual_style)
        design_chars = max(design_chars, len(prompt) + len(head))

    return {
        "prompt": prompt,
        "prompt_headshot": head,
        "design_chars": design_chars,
        "raw": content,
        "parsed": parsed,
        "notes": notes,
        "wh_ratio": ratio,
        "model": resp.get("model", model),
        "tier": tier,
        "tier_zh": D.TIER_META[tier]["zh"],
        "style": style_key,
        "style_zh": style_zh,
        "visual_style": visual_style,
        "visual_style_zh": style_label(visual_style),
        "composition": composition,
        "composition_zh": COMPOSITION_LABELS.get(composition, composition),
        "usage": resp.get("usage", {}),
    }


def _ensure_style_prefix(text: str, visual_style) -> str:
    """Put the style phrase at the front of the prompt if it is not already there."""
    text = (text or "").strip()
    phrase = style_phrase(visual_style)
    if not phrase:
        return text
    lead = phrase.split(",")[0].strip()
    if lead and lead.lower() in text[:160].lower():
        return text
    return f"{phrase}. {text}" if text else phrase


def _salvage_field(text: str, field: str) -> str | None:
    """Pull one quoted string field even when the JSON is truncated or malformed."""
    import re
    m = re.search(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)' % re.escape(field), text or "")
    if not m:
        return None
    s = m.group(1)
    try:
        return json.loads(f'"{s}"')
    except Exception:
        return s.replace("\\n", "\n").replace('\\"', '"').strip()


def _salvage_prompt(text: str) -> str | None:
    v = _salvage_field(text or "", "rewritten_prompt")
    if not v:
        return None
    v = v.strip()
    return v or None


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("\n", 1)
        t = parts[1] if len(parts) > 1 else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
        t = t.strip()
    a, b = t.find("{"), t.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        return json.loads(t[a:b + 1])
    except json.JSONDecodeError:
        pass
    # A small local model often answers with a LIST of single-key objects and
    # forgets the opening bracket: {"rewritten_prompt": "..."}, {"wh_ratio":
    # "2:3"}] . json.loads cannot read that, so the bracket is restored and
    # the objects are merged back into one flat dict.
    repaired = _repair_json_list(t)
    if repaired is not None:
        return repaired
    return None


def _repair_json_list(t: str) -> dict | None:
    """Turn a bracketed-less list of JSON objects back into one flat dict."""
    if not t:
        return None
    # The broken shape ends with ']' and starts with '{'.
    if not t.endswith("]"):
        return None
    body = t[:-1].rstrip()
    if not body.startswith("{"):
        return None
    # Split into top-level objects, respecting string literals.
    objs: list[dict] = []
    depth = 0
    in_str = False
    esc = False
    start = 0
    for i, ch in enumerate(body):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                chunk = body[start:i + 1]
                try:
                    o = json.loads(chunk)
                except json.JSONDecodeError:
                    return None
                if isinstance(o, dict):
                    objs.append(o)
    if len(objs) < 2:
        return None
    merged: dict = {}
    for o in objs:
        merged.update(o)
    return merged


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    ms = probe_models()
    ok = [m for m in ms if m.get("status") == "ok"]
    print(f"models={len(ms)}  ok={len(ok)}")
    for m in ms[:12]:
        print(f"  {m['status']:6} {m['ms']:5}ms  {m['id']}")
