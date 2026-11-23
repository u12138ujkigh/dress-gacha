# -*- coding: utf-8 -*-
"""Visual style taxonomy: four media families with their sub-styles.

Split from the category axis on purpose. Category decides WHAT is worn; style
decides HOW the picture is made. Style also drives the character design itself:
skin rendering, makeup finish and fabric response all have to match the medium,
and the style phrase is prefixed to the emitted prompt.

Each sub carries:
    key      stable id
    zh       Chinese label
    en       English phrase, put at the FRONT of the prompt
    zh_note  one-line Chinese description for the UI tooltip
    family   which of the four media families it belongs to, so the model can be
             told "this is a photograph, not an illustration" (or the reverse)
"""
from __future__ import annotations

STYLE_TREE: list[dict] = [
    {
        "key": "photo",
        "zh": "写实摄影类",
        "en": "realistic photography",
        "subs": [
            ("photo_documentary", "纪实",
             "documentary photograph, available light, candid and unposed, honest texture, reportage framing",
             "真实抓拍，现场光，不摆拍，质感朴素可信"),
            ("photo_portrait", "人像",
             "portrait photograph, controlled key light with fill, sharp focus on the eyes, shallow depth of field, natural skin texture retained",
             "影棚或环境人像，眼神光清晰，皮肤保留真实纹理"),
            ("photo_landscape", "风光",
             "landscape photograph, wide vista, layered atmospheric depth, natural daylight, high dynamic range",
             "大场景开阔视野，远近层次与空气感"),
            ("photo_architecture", "建筑",
             "architectural photograph, corrected verticals, precise geometry, even ambient light, structural lines as the composition",
             "垂直线条平直，几何结构为构图骨架"),
            ("photo_product", "产品",
             "product photograph, seamless background, even studio lighting, crisp edge definition, controlled reflections",
             "无缝背景，布光均匀，边缘干净，反光可控"),
            ("photo_food", "美食",
             "food photograph, directional soft light, glistening highlights on moisture and sauce, shallow depth of field, warm appetising colour",
             "侧向柔光，油光与酱汁高光，暖调诱人"),
            ("photo_street", "街拍",
             "street photograph, handheld, environmental context, mid-step motion, real urban light, slight grain",
             "手持抓拍，环境入画，行进中的人物"),
            ("photo_cinematic", "电影感",
             "cinematic photograph, widescreen framing, anamorphic shallow focus, teal and orange grade, filmic contrast and halation",
             "宽画幅，浅景深，青橙调色，胶片反差"),
            ("photo_film", "胶片",
             "analog film photograph, visible grain, halation on highlights, slight light leak, natural colour shift, soft highlight rolloff",
             "颗粒、高光溢出、轻微漏光、色彩自然偏移"),
            ("photo_bw", "黑白",
             "black and white photograph, true monochrome, deep blacks with retained shadow detail, silver-gelatin tonality",
             "纯黑白，暗部有层次，银盐质感"),
            ("photo_angle", "特殊视角",
             "special viewpoint photograph: low angle, top down, dutch tilt, extreme wide or macro perspective, deliberate perspective distortion",
             "低角度、俯拍、倾斜、超广角或微距"),
        ],
    },
    {
        "key": "paint",
        "zh": "绘画插画类",
        "en": "painting and illustration",
        "subs": [
            ("paint_oil", "油画",
             "oil painting, visible brushwork, thick impasto on the lights, glazed shadows, canvas weave, layered pigment",
             "可见笔触，亮部厚涂，暗部罩染，画布纹理"),
            ("paint_watercolor", "水彩",
             "watercolour painting, wet-on-wet bleeding, transparent layered washes, dry brush edges, reserved white paper",
             "湿画晕染，透明叠色，干笔边缘，留白纸面"),
            ("paint_sketch", "素描线稿",
             "pencil and charcoal drawing, visible line weight variation, hatching for shadow, unshaded paper showing through",
             "线条轻重变化，排线做阴影，纸面留白"),
            ("paint_ink", "国画水墨",
             "Chinese ink painting, brush-written line, splashed and pooled ink, graded wash, generous negative space, seal-red accent",
             "毛笔线条，泼墨与积墨，留白，朱印点缀"),
            ("paint_print", "版画",
             "printmaking, carved relief line, flat ink blocks, slight misregistration, paper grain impressed by the plate",
             "刻痕线条，平涂色块，轻微套色错位，压印纸纹"),
            ("paint_thick", "厚涂",
             "thick-paint digital rendering, opaque painterly strokes, sculpted form through value, no hard line work",
             "不透明笔触堆叠，靠明暗塑形，无线稿"),
            ("paint_flat", "扁平",
             "flat illustration, solid colour shapes, no gradients, minimal geometric detail, clean silhouettes",
             "纯色块面，无渐变，几何化，轮廓干净"),
            ("paint_picturebook", "绘本",
             "children's picture-book illustration, soft textured colour, gentle rounded shapes, warm naive charm, hand-made feel",
             "柔和肌理，圆润造型，温暖手作感"),
            ("paint_comic", "漫画",
             "comic illustration, confident ink line, halftone or crosshatch shading, bold panel-ready composition",
             "肯定墨线，网点或排线阴影，画面适合分格"),
            ("paint_decorative", "装饰",
             "decorative illustration, ornamental pattern integration, stylised symmetry, refined line and gold accent",
             "纹样融入，程式化对称，线条与金箔感"),
            ("paint_collage", "拼贴",
             "collage, cut paper and torn magazine fragments, layered edges with visible shadow, mixed printed texture",
             "剪纸与撕纸拼贴，边缘有厚度阴影，混合印刷质感"),
        ],
    },
    {
        "key": "cartoon",
        "zh": "卡通动漫类",
        "en": "cartoon and anime",
        "subs": [
            ("anime_jp", "日系二次元",
             "Japanese anime illustration, clean cel line, large expressive eyes with layered iris highlights, soft gradient hair shading",
             "干净赛璐璐线稿，大眼分层高光，头发渐变"),
            ("anime_cn", "国漫",
             "Chinese animation illustration, refined line with ink influence, elegant elongated proportions, restrained colour",
             "线条带国画影响，身形修长，用色克制"),
            ("cartoon_us", "美式卡通",
             "American cartoon, bold contour line, exaggerated proportions, rubbery limb shapes, saturated flat colour",
             "粗轮廓线，夸张比例，弹性肢体，饱和平涂"),
            ("chibi", "Q版",
             "chibi super-deformed character, two to three head heights, oversized head, tiny body, simplified features",
             "二到三头身，大头小身，五官简化"),
            ("manga", "漫画风",
             "manga style, screentone shading, sharp ink line, dramatic speed lines and high contrast blacks",
             "网点阴影，锐利墨线，速度线与大面积黑"),
            ("cel", "赛璐璐",
             "cel-shaded anime frame, flat colour fields with a single hard shadow tone, crisp outline, animation-still look",
             "平涂色块加单层硬阴影，锐利描边，动画原帧感"),
            ("pixel", "像素",
             "pixel art, deliberate low resolution, visible pixel grid, limited palette, dithering for gradients",
             "低分辨率像素格，有限色板，抖动渐变"),
            ("artoy", "潮玩",
             "designer toy render, glossy vinyl surface, rounded simplified sculpt, studio product lighting",
             "亮面塑胶质感，圆润简化造型，棚拍布光"),
            ("sticker", "表情包",
             "sticker illustration, heavy bold outline, exaggerated comic expression, plain flat fill, readable at small size",
             "粗重描边，夸张表情，纯色填充，小尺寸可读"),
            ("anime3d", "3D动漫",
             "3D anime character, toon-shaded 3D model, clean rim light, stylised hair as sculpted strands, cel-like shading bands",
             "三渲二模型，边缘光，雕塑感发丝，赛璐璐式色阶"),
        ],
    },
    {
        "key": "render3d",
        "zh": "3D渲染类",
        "en": "3D render",
        "subs": [
            ("r3d_real", "写实3D",
             "photoreal 3D render, physically based materials, subsurface scattering on skin, accurate global illumination, ray-traced reflections",
             "PBR 材质，皮肤次表面散射，全局光照，光线追踪反射"),
            ("r3d_toon", "卡通3D",
             "toon-shaded 3D render, hard banded shadow steps, clean inverted-hull outline, saturated flat albedo",
             "硬色阶阴影，反向外扩描边，饱和平涂固有色"),
            ("r3d_anime", "3D动漫",
             "3D anime render, cel-shaded model with anime proportion, stylised sculpted hair, soft bloom on highlights",
             "赛璐璐着色的动漫比例模型，雕塑发丝，高光柔光晕"),
            ("lowpoly", "低多边形",
             "low-poly 3D render, faceted planar surfaces, visible triangulation, flat per-face shading, minimal detail",
             "平面化三角面，明显棱面，逐面平涂"),
            ("clay", "黏土",
             "clay render, matte plasticine surface with subtle fingerprints, rounded soft sculpt, soft studio light, shallow depth of field",
             "哑光橡皮泥质感，轻微指痕，圆润软雕塑"),
            ("blindbox", "盲盒潮玩",
             "blind-box collectible figure, glossy vinyl with matte fabric accents, chibi proportion, clean seam lines, display-base lighting",
             "亮面塑胶配哑光布料，Q版比例，分模线干净"),
            ("c4d_commerce", "C4D电商",
             "C4D e-commerce render, clean studio setup, soft gradient background, precise softbox reflections, commercial polish",
             "干净棚拍布景，渐变背景，柔光箱反射，商业质感"),
            ("isometric", "等距",
             "isometric 3D view, orthographic projection, 30-degree axis alignment, uniform scale, crisp edges",
             "正交投影，30 度轴对齐，等比缩放，边缘锐利"),
            ("archviz", "建筑可视化",
             "architectural visualisation, balanced daylight with interior fill, realistic material scale, corrected perspective, ambient occlusion in corners",
             "日光与室内补光平衡，材质尺度真实，透视校正"),
            ("material_closeup", "材质特写",
             "extreme material close-up, macro detail showing surface grain and micro relief, raking light to reveal texture, shallow focus falloff",
             "微距展示表面颗粒与微观起伏，侧向掠射光"),
        ],
    },
]

# Flat index: sub key -> (family, sub)
SUB_INDEX: dict[str, tuple[dict, dict]] = {}
for _f in STYLE_TREE:
    for _s in _f["subs"]:
        SUB_INDEX[_s[0]] = (_f, {
            "key": _s[0], "zh": _s[1], "en": _s[2], "zh_note": _s[3],
        })

# Picking only the big family still needs a phrase for the prompt.
FAMILY_BRIEF = {
    "photo": "realistic photograph, true lens rendering, physical light and material response",
    "paint": "hand-painted illustration, visible pigment and brushwork, non-photographic surface",
    "cartoon": "cartoon or anime illustration, clean line work and flat colour",
    "render3d": "3D digital render, modelled geometry with physically based shading",
}

# Whether the family renders like a camera or like a drawn/sculpted medium. The
# model is told this explicitly so it does not produce a photo for a painting
# style, or an illustration for a photographic one.
FAMILY_KIND = {
    "photo": "photographic",
    "paint": "drawn",
    "cartoon": "drawn",
    "render3d": "rendered",
}


def resolve_multi(keys: list[str]) -> tuple[str, str, set[str]]:
    """Resolve a selection to (label_zh, english_clause, families).

    The families set lets the caller tell the model which medium it is working in.
    """
    labels: list[str] = []
    phrases: list[str] = []
    families: set[str] = set()
    seen_label: set[str] = set()
    seen_phrase: set[str] = set()

    for k in keys or []:
        if k in SUB_INDEX:
            fam, sub = SUB_INDEX[k]
            lab = f"{fam['zh']}·{sub['zh']}"
            ph = sub["en"]
            families.add(fam["key"])
        else:
            fam = next((c for c in STYLE_TREE if c["key"] == k), None)
            if not fam:
                continue
            lab = fam["zh"]
            ph = FAMILY_BRIEF.get(k, fam["en"])
            families.add(fam["key"])
        if lab not in seen_label:
            labels.append(lab)
            seen_label.add(lab)
        if ph not in seen_phrase:
            phrases.append(ph)
            seen_phrase.add(ph)

    if not labels:
        return "不指定", "", set()
    return " + ".join(labels), ", ".join(phrases), families


def as_tree() -> list[dict]:
    return [
        {
            "key": c["key"], "zh": c["zh"], "en": c["en"],
            "subs": [{"key": s[0], "zh": s[1], "en": s[2], "note": s[3]} for s in c["subs"]],
        }
        for c in STYLE_TREE
    ]


def total_nodes() -> int:
    return len(STYLE_TREE) + len(SUB_INDEX)
