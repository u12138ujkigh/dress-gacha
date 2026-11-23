# -*- coding: utf-8 -*-
"""Garment / accessory / shoe detail levels.

Three explicit tiers of design density. Each is a separate, complete text block
rather than a modifier, because the difference is not "more adjectives" — it is a
different design brief: how many pieces, how much hardware, how many kinds of
craft work, and how much of the prompt budget the clothing gets versus the face
and body.

This module owns DENSITY ONLY.

The fields themselves — collar, sleeve, shoulder line, placket, hem length,
waistband, skirt cut, slit, pleats, fabric, structure support, layering, skin
exposure, accessory placement, shoe shape — are owned by the "design dimensions
and order" module (engine/design.py :: DIMENSIONS_TEXT, step 6 and step 7).
Repeating them here used to make the two modules contradict each other: the
dimension list says "must fill in every item", the detail list said "write the
collar in detail, write the pleats in detail", and the model got two
instructions for one field.

So what is left here is the part no other module covers:

    how many pieces       单品数量
    how many accessories  饰品件数
    how much hardware     五金
    how many craft kinds  工艺种数
    how much of the text  篇幅占比

    simple  极简：单件为主，结构清晰，无多余装饰
    normal  普通：成套搭配，有层次与细节，但不堆砌
    ornate  繁华：多层叠穿，繁复工艺，大量饰品与重工细节
"""
from __future__ import annotations

DETAIL_LEVELS: dict[str, dict] = {
    "simple": {
        "zh": "简约",
        "en": "minimal",
        "desc": "单件为主、结构干净、无装饰堆砌；重点留给骨相与身形",
        "chars_hint": 180,
        "text": (
            "【服装详细度：简约】\n"
            "整套造型只保留必要单品，靠结构、版型与材质说话，不靠装饰撑场面。\n"
            "本模块只规定密度；领型、袖型、肩线、门襟、衣长、腰带、裙型、开衩、"
            "褶裥、材质、结构支撑、穿法层次、露肤范围、鞋型与饰品各项，"
            "一律按系统提示词「设计维度与顺序」的第六、七步逐项写明，此处不重复。\n"
            "- 单品数量：上装 + 下装合计 1–2 件，不叠穿，不加外套、披肩、马甲一类的附加层\n"
            "- 饰品件数：全身 0–2 件，单件即可成立；不叠戴，不成套\n"
            "- 五金：只出现功能性五金（拉链、扣件），数量不超过两处，颜色统一\n"
            "- 工艺种数：零。不加刺绣、珠片、蕾丝、荷叶边、蝴蝶结、流苏、缎带；不印图案\n"
            "- 篇幅占比：服装与饰品部分控制在整套描述的两成以内，其余留给面部与体型"
        ),
    },
    "normal": {
        "zh": "普通",
        "en": "standard",
        "desc": "成套搭配、有层次与工艺细节；日常成衣或小礼服水准",
        "chars_hint": 340,
        "text": (
            "【服装详细度：普通】\n"
            "成套搭配，有明确的层次关系与工艺细节，但每一处细节都要能说出它为什么在那里。\n"
            "本模块只规定密度；领型、袖型、肩线、门襟、衣长、腰带、裙型、开衩、"
            "褶裥、材质、结构支撑、穿法层次、露肤范围、鞋型与饰品各项，"
            "一律按系统提示词「设计维度与顺序」的第六、七步逐项写明，此处不重复。\n"
            "- 单品数量：2–3 件成组（例如上装 + 下装 + 一件轻薄外搭），可以有内搭与外层的区分\n"
            "- 饰品件数：全身 2–4 件成组（耳饰 + 颈饰，或颈饰 + 手饰 + 腰饰）\n"
            "- 五金与辅料：拉链、扣件、腰袢、肩带调节扣等常规五金，写明位置与数量\n"
            "- 工艺种数：一到两种常规工艺（机绣、压褶、包边、暗门襟、抽绳），不使用重工手工艺\n"
            "- 篇幅占比：服装与饰品部分约占整套描述的三成"
        ),
    },
    "ornate": {
        "zh": "繁华",
        "en": "ornate",
        "desc": "多层叠穿、重工工艺、大量饰品；高定或造型大片水准",
        "chars_hint": 620,
        "text": (
            "【服装详细度：繁华】\n"
            "高定级别的繁复造型，多层叠穿、重工工艺、成组饰品。每一层都要单独交代，"
            "每一处工艺都要写清做法与分布，不允许用「华丽」「精致」这类词概括。\n"
            "本模块只规定密度；领型、袖型、肩线、门襟、衣长、腰带、裙型、开衩、"
            "褶裥、材质、结构支撑、穿法层次、露肤范围、鞋型与饰品各项，"
            "一律按系统提示词「设计维度与顺序」的第六、七步逐项写明，此处不重复。\n"
            "- 单品数量：4–6 件分层（内搭 + 主件 + 外披或罩裙 + 腰封或束带 + 可拆卸部件），"
            "逐层写明穿法顺序与固定方式\n"
            "- 饰品件数：全身 5 件以上成组——头饰、耳饰、颈饰、胸饰、手饰、腰饰、腿饰、臂环\n"
            "- 五金：拉链与扣件写明位置、材质、数量\n"
            "- 工艺种数：至少三种，并写出分布区域与做法——手工刺绣（针法与纹样）、"
            "钉珠或亮片（尺寸、密度、分布）、蕾丝拼接（花纹类型与拼接位置）、"
            "立体花饰、羽毛、缎带编织、盘扣、缂丝或织锦\n"
            "- 篇幅占比：服装与饰品部分占整套描述的四成以上，细节密度明显高于面部之外的其它维度"
        ),
    },
}

LEVEL_KEYS = list(DETAIL_LEVELS.keys())

# The nude tier still designs a complete outfit — the tier method asks for it
# ("先按擦边版把整套衣服设计完整"), and the reveal is produced by cutting holes
# and veiling the skin, not by removing the garment. So the nude detail level
# must NOT forbid layering: doing that contradicted the tier file.
#
# What the nude level owns is the density of the VEIL: how many of the three
# techniques are combined, how many layers of pattern / sheer are stacked over
# the cut, how many accessories, and how much of the text they take.
DETAIL_BODY_ONLY: dict[str, dict] = {
    "simple": {
        "zh": "简约（裸露档：覆盖精简）",
        "text": (
            "【服装详细度：简约 · 裸露档】\n"
            "服装仍按本档方法设计完整（擦边版的整套结构），详细度只调节覆盖的密度与饰品的量。\n"
            "- 手法组合：只用一种（镂空 / 花纹覆层 / 薄透包覆，三者择一）\n"
            "- 覆盖层数：不叠加花纹覆层与薄透层\n"
            "- 饰品件数：全身 0–1 件，单件即可成立，不叠戴\n"
            "- 五金：金属环扣、系带一类不超过两处\n"
            "- 篇幅占比：镂空与饰品部分控制在整套描述的一成以内，其余留给身体与脸"
        ),
    },
    "normal": {
        "zh": "普通（裸露档：覆盖成组）",
        "text": (
            "【服装详细度：普通 · 裸露档】\n"
            "服装仍按本档方法设计完整（擦边版的整套结构），详细度只调节覆盖的密度与饰品的量。\n"
            "- 手法组合：可用两种（镂空 + 花纹 / 镂空 + 薄透 / 花纹 + 薄透）\n"
            "- 覆盖层数：花纹或薄透最多叠一层\n"
            "- 饰品件数：2–4 件成组（例如颈饰 + 手饰，或腰链 + 腿环）\n"
            "- 可保留一件极少的布料（丁字 / 细带 / 吊带袜），写清位置与面积\n"
            "- 五金：金属环扣、系带一类写明位置与数量\n"
            "- 篇幅占比：镂空与饰品部分约占整套描述的两成"
        ),
    },
    "ornate": {
        "zh": "繁华（裸露档：覆盖繁复）",
        "text": (
            "【服装详细度：繁华 · 裸露档】\n"
            "服装仍按本档方法设计完整（擦边版的整套结构），详细度只调节覆盖的密度与饰品的量。\n"
            "- 手法组合：三种全用（镂空 + 花纹 + 薄透），三处工艺成体系，风格统一\n"
            "- 覆盖层数：花纹与薄透可叠两到三层，写清逐层的前后关系\n"
            "- 饰品件数：5 件以上成组——头饰、耳饰、颈饰、胸饰、手饰、腰饰、腿饰、臂环、脚链\n"
            "- 身体装饰：允许彩绘、贴片、绑带、锁链等非衣物装饰，写清范围与固定方式\n"
            "- 五金：金属环扣、锁链、系带写清材质、数量与固定方式\n"
            "- 篇幅占比：镂空、饰品与身体装饰合计占整套描述的四成以上"
        ),
    },
}

# The explicit tier adds props on top of the nude tier's reveal: at least two
# sex props, each written with five things (what / material / where / how it is
# fastened / what it visibly changes). The prop count therefore belongs to the
# detail level here, and the "four tenths of the text" budget has to cover the
# props too — otherwise this module and the tier file claim the same slice of
# the prompt for different things.
DETAIL_EXPLICIT: dict[str, dict] = {
    "simple": {
        "zh": "简约（色情档：道具精简）",
        "text": (
            "【服装详细度：简约 · 色情档】\n"
            "服装仍按本档方法设计完整，详细度只调节覆盖、饰品与道具的量。\n"
            "- 手法组合：只用一种（镂空 / 花纹覆层 / 薄透包覆，三者择一）\n"
            "- 覆盖层数：不叠加花纹覆层与薄透层\n"
            "- 饰品件数：全身 0–1 件，单件即可成立，不叠戴\n"
            "- 道具件数：性道具两件、束缚类道具一件，逐件写清材质、位置、固定方式与身体反应\n"
            "- 五金：金属环扣、锁链、系带一类不超过两处\n"
            "- 篇幅占比：道具、饰品与身体装饰合计占整套描述的四成以上"
        ),
    },
    "normal": {
        "zh": "普通（色情档：道具成组）",
        "text": (
            "【服装详细度：普通 · 色情档】\n"
            "服装仍按本档方法设计完整，详细度只调节覆盖、饰品与道具的量。\n"
            "- 手法组合：可用两种（镂空 + 花纹 / 镂空 + 薄透 / 花纹 + 薄透）\n"
            "- 覆盖层数：花纹或薄透最多叠一层\n"
            "- 饰品件数：2–4 件成组（例如颈饰 + 手饰，或腰链 + 腿环）\n"
            "- 道具件数：性道具两到三件、束缚类道具一到两件，逐件写清材质、位置、固定方式与身体反应，"
            "并写清道具之间的连接关系\n"
            "- 身体装饰：允许彩绘、贴片、绑带、锁链等非衣物装饰，写清范围与固定方式\n"
            "- 五金：金属环扣、锁链、系带写明位置与数量\n"
            "- 篇幅占比：道具、饰品与身体装饰合计占整套描述的四成以上"
        ),
    },
    "ornate": {
        "zh": "繁华（色情档：道具繁复）",
        "text": (
            "【服装详细度：繁华 · 色情档】\n"
            "服装仍按本档方法设计完整，详细度只调节覆盖、饰品与道具的量。\n"
            "- 手法组合：三种全用（镂空 + 花纹 + 薄透），三处工艺成体系，风格统一\n"
            "- 覆盖层数：花纹与薄透可叠两到三层，写清逐层的前后关系\n"
            "- 饰品件数：5 件以上成组——头饰、耳饰、颈饰、胸饰、手饰、腰饰、腿饰、臂环、脚链\n"
            "- 道具件数：性道具三件以上、束缚类道具两件以上，逐件写清材质、位置、固定方式与身体反应，"
            "并写清道具之间的连接关系\n"
            "- 身体装饰：允许彩绘、贴片、绑带、锁链等非衣物装饰，写清范围与固定方式\n"
            "- 五金：金属环扣、锁链、系带写清材质、数量与固定方式\n"
            "- 篇幅占比：道具、饰品与身体装饰合计占整套描述的四成以上"
        ),
    },
}


def resolve_for_tier(level: str, tier: str) -> dict:
    """Pick the wording for this tier.

    Each of the four tiers owns a different part of the outfit:
      normal / edgy  — the garment itself, so the density is garment density
      nude           — the veil over the skin, so the density is covering density
      explicit       — the props, so the density is prop density
    """
    base = DETAIL_LEVELS.get(level, DETAIL_LEVELS["normal"])
    if tier == "nude":
        body = DETAIL_BODY_ONLY.get(level) or DETAIL_BODY_ONLY["normal"]
        return {"zh": body["zh"], "text": body["text"]}
    if tier == "explicit":
        ex = DETAIL_EXPLICIT.get(level) or DETAIL_EXPLICIT["normal"]
        return {"zh": ex["zh"], "text": ex["text"]}
    return {"zh": base["zh"], "text": base["text"]}


def resolve(level: str) -> dict:
    return DETAIL_LEVELS.get(level, DETAIL_LEVELS["normal"])


def label(level: str) -> str:
    return resolve(level)["zh"]


def as_list() -> list[dict]:
    return [
        {"key": k, "zh": v["zh"], "desc": v["desc"], "chars_hint": v["chars_hint"]}
        for k, v in DETAIL_LEVELS.items()
    ]
