# -*- coding: utf-8 -*-
"""Compose one draw from the lexicon: pick, assemble, narrate."""
from __future__ import annotations

import hashlib
import random
from typing import Any

from . import lexicon as L

TIERS = L.TIERS
STYLE_KEYS = list(L.STYLES.keys())

# The lexicon mode owns a hand-written garment pool per family, so it cannot use
# the 18-category taxonomy directly. This maps each of its 16 families onto one
# taxonomy node, so the UI can present both modes under the same tree: the big
# class is the category, the small class is this family.
import os as _os
from . import taxonomy as _T

# family key -> (category key, sub key)
FAMILY_NODE = {
    "satin_gown":  ("formal", "frm_gown"),
    "wedding":     ("formal", "frm_bridal"),
    "cheongsam":   ("historical", "his_qing"),
    "hanfu":       ("eastern_fantasy", "ef_xianxia"),
    "office":      ("career", "car_finance"),
    "nurse":       ("career", "car_medical"),
    "stewardess":  ("career", "car_service"),
    "teacher":     ("career", "car_finance"),
    "swimsuit":    ("intimates", "int_swim"),
    "lingerie":    ("roleplay", "rp_material"),
    "lolita":      ("subculture", "sub_lolita"),
    "sleepwear":   ("intimates", "int_sleep"),
    "leather":     ("scifi", "sf_wasteland"),
    "sportswear":  ("activewear", "act_indoor"),
    "yukata":      ("historical", "his_world"),
    "idol_stage":  ("acg", "acg_idol"),
}


def family_for_node(node_key: str) -> str | None:
    """Reverse lookup: a taxonomy node -> the lexicon family that covers it."""
    for fam, (cat, sub) in FAMILY_NODE.items():
        if node_key in (cat, sub):
            return fam
    return None


def families_for_node(node_key: str) -> list[str]:
    """Every lexicon family covered by a taxonomy category (or a single sub)."""
    out = []
    for fam, (cat, sub) in FAMILY_NODE.items():
        if node_key in (cat, sub):
            out.append(fam)
    return out


def covered_tree() -> list[dict]:
    """The taxonomy pruned to what this mode can actually draw.

    A node with no family behind it would silently fall back to a random family,
    which reads as the tool ignoring the pick — so such nodes are not offered.
    """
    out = []
    for c in _T.CATEGORIES:
        fams = families_for_node(c["key"])
        subs = []
        for s in c["subs"]:
            sub_fams = families_for_node(s[0])
            if sub_fams:
                subs.append({
                    "key": s[0], "zh": s[1], "brief": s[2], "items": s[3],
                    "families": sub_fams,
                })
        if not fams and not subs:
            continue
        out.append({
            "key": c["key"], "zh": c["zh"], "en": c["en"], "brief": c["brief"],
            "families": fams, "subs": subs,
        })
    return out


def _resolve_family(style: str, rng: random.Random) -> str:
    """Turn a style selector into one lexicon family key.

    Unknown or uncovered selectors raise rather than silently drawing a random
    family: a pick the pool cannot honour must be visible, not ignored.
    """
    if not style or style == "random":
        return rng.choice(STYLE_KEYS)
    if style in L.STYLES:
        return style
    fams = families_for_node(style)
    if fams:
        return rng.choice(fams)
    raise ValueError(
        f"词库模式没有覆盖该品类：{style}（词库只覆盖 16 个手写服装族）"
    )

AGE_SUBJECTS = [
    "a beautiful young East Asian woman in her early twenties",
    "a beautiful young East Asian woman, early to mid twenties",
    "a stunning young East Asian woman in her twenties",
]

VIEWS = {
    "front": "front view, facing the camera, full body visible",
    "back": "back view, seen from behind, full body visible",
    "three_quarter": "three-quarter view, body angled away, face turned toward the camera",
}

# Where the shot happens: seamless studio (the reference look) or a real location.
BACKDROPS = ("studio", "real", "random")


def _pick(rng: random.Random, seq):
    return rng.choice(seq)


def draw_one(
    tier: str = "normal",
    style: str = "random",
    seed: int | None = None,
    view: str = "random",
    backdrop: str = "studio",
) -> dict[str, Any]:
    """Compose a single draw. Deterministic for a given (tier, style, seed, view, backdrop).

    `style` may be a lexicon family key, a taxonomy category/sub key, or 'random'.
    Taxonomy nodes are mapped back to the family whose garment pool covers them;
    a category with several families picks one at random for this draw.
    """
    if tier not in TIERS:
        raise ValueError(f"unknown tier: {tier}")
    if backdrop not in BACKDROPS:
        backdrop = "studio"

    if seed is None:
        seed = random.randrange(0, 2**32 - 1)
    else:
        seed = int(seed)

    rng = random.Random(seed)

    style_key = _resolve_family(style, rng)

    st = L.STYLES[style_key]
    garment = _pick(rng, L.GARMENT[style_key][tier])
    pose = _pick(rng, L.POSES[tier])
    expr = _pick(rng, L.EXPRESSIONS[tier])
    acc = _pick(rng, L.ACCESSORIES[tier])
    prop = _pick(rng, L.PROPS[tier])
    light = _pick(rng, L.LIGHTING)
    framing = _pick(rng, L.FRAMING)
    hair = _pick(rng, L.HAIR)
    makeup = _pick(rng, L.MAKEUP)
    imperf = _pick(rng, L.IMPERFECTIONS)
    body = _pick(rng, st["bodies"])
    palette = _pick(rng, st["palette"])
    subject = _pick(rng, AGE_SUBJECTS)
    view_key = view if view in VIEWS else rng.choice(list(VIEWS.keys()))
    view_txt = VIEWS[view_key]
    story = _pick(rng, L.TIER_STORY[tier])

    if backdrop == "random":
        backdrop = rng.choice(["studio", "real"])
    if backdrop == "studio":
        scene = _pick(rng, L.STUDIO_BACKDROPS)
        prop = ""  # a seamless set carries no props
    else:
        scene = _pick(rng, st["scenes"])

    parts = [
        L.QUALITY,
        subject,
        body,
        palette,
        garment,
        hair,
        makeup,
        acc,
        pose,
        expr,
        prop,
        scene,
        light,
        framing,
        view_txt,
        imperf,
    ]
    prompt = ", ".join(p.strip().rstrip(",") for p in parts if p and p.strip())
    negative = L.NEGATIVE_BY_TIER.get(tier, "") + L.NEGATIVE_BASE

    meta_zh = (
        f"{L.TIER_META[tier]['zh']} · {st['zh']} · "
        f"{'棚拍' if backdrop == 'studio' else '实景'} · "
        f"{view_key.replace('_', '/')}"
    )
    handle = _short_zh(garment)
    title_zh = f"{st['zh']}·{handle}" if handle != st["zh"] else st["zh"]

    digest = hashlib.sha1(
        f"{tier}|{style_key}|{seed}|{view_key}|{backdrop}".encode()
    ).hexdigest()[:10]

    return {
        "id": digest,
        "tier": tier,
        "tier_zh": L.TIER_META[tier]["zh"],
        "style": style_key,
        "style_zh": st["zh"],
        "seed": seed,
        "view": view_key,
        "backdrop": backdrop,
        "title_zh": title_zh,
        "meta_zh": meta_zh,
        "prompt": prompt,
        "negative": negative,
        "narrative_zh": story,
        "slots": {
            "garment": garment,
            "hair": hair,
            "makeup": makeup,
            "accessories": acc,
            "pose": pose,
            "expression": expr,
            "props": prop,
            "scene": scene,
            "lighting": light,
            "framing": framing,
            "body": body,
            "palette": palette,
        },
    }


def _short_zh(garment_en: str) -> str:
    """A compact Chinese handle for the card title, derived from the garment text."""
    table = [
        ("off-shoulder", "一字肩"), ("one-shoulder", "单肩"), ("strapless", "抹胸"),
        ("backless", "露背"), ("plunging", "深V"), ("slit", "开叉"),
        ("sheer", "薄透"), ("lace", "蕾丝"), ("satin", "缎面"),
        ("leather", "皮革"), ("uniform", "制服"), ("yukata", "浴衣"),
        ("hanfu", "汉服"), ("qipao", "旗袍"), ("wedding", "婚纱"),
        ("lolita", "洛丽塔"), ("swimsuit", "泳装"), ("bikini", "比基尼"),
        ("topless", "上身裸"), ("nude", "全裸"), ("pierced", "穿孔"),
        ("bondage", "束缚"), ("collar", "项圈"), ("rope", "绳缚"),
        ("stockings", "丝袜"), ("garter", "吊袜"), ("robe", "长袍"),
    ]
    low = garment_en.lower()
    hits = [zh for en, zh in table if en in low]
    return "".join(hits[:2]) if hits else "造型"


def draw_many(
    tier: str = "normal",
    style: str = "random",
    count: int = 1,
    base_seed: int | None = None,
    view: str = "random",
    backdrop: str = "studio",
    unique: bool = True,
) -> list[dict[str, Any]]:
    """Compose `count` draws. Seeds are sequential from base_seed for reproducibility."""
    count = max(1, min(int(count), 200))
    if base_seed is None:
        base_seed = random.randrange(0, 2**32 - 1)
    base_seed = int(base_seed)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    i = 0
    guard = 0
    while len(out) < count and guard < count * 40:
        guard += 1
        item = draw_one(tier=tier, style=style, seed=base_seed + i,
                        view=view, backdrop=backdrop)
        i += 1
        if unique and item["prompt"] in seen:
            continue
        seen.add(item["prompt"])
        out.append(item)
    return out


def matrix_stats() -> dict[str, Any]:
    m = L.style_tier_matrix()
    per_tier = {t: sum(m[s][t] for s in m) for t in TIERS}
    return {
        "per_style": m,
        "per_tier": per_tier,
        "total": sum(per_tier.values()),
        "styles": {k: v["zh"] for k, v in L.STYLES.items()},
        "tiers": L.TIER_META,
        "backdrops": {
            "studio": "棚拍无缝",
            "real": "实景",
            "random": "随机",
        },
        "studio_backdrops": L.STUDIO_BACKDROPS,
        # What this mode can actually draw, pruned from the full taxonomy.
        "tree": covered_tree(),
    }
