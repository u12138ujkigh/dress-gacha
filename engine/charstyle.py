# -*- coding: utf-8 -*-
"""Character style tags: the PEOPLE axis.

Three axes now compose a picture:

    category  → what is worn
    visual    → how it is shot / rendered  (画风)
    character → who the person reads as    (人物风格)

Order matters and is reflected in the assembled prompt: art style first, then
character style, then the design. The character tag is not decoration — it
changes proportion, makeup weight, expression, gesture and the garment
tendency, so each entry carries an explicit design instruction rather than a
label.

All tags describe adult figures. The age-adjacent ones (萝莉 / 幼态 / 少女) name
a visual archetype — petite frame, youthful makeup and styling — applied to an
adult model, which matches the hard rule already stated in every tier document.
"""
from __future__ import annotations

CHAR_TREE: list[dict] = [
    {
        "key": "age",
        "zh": "年龄感",
        "en": "age impression",
        "subs": [
            ("cs_loli", "萝莉",
             "petite adult figure with stylized proportions: short overall height, noticeably below average, "
             "slightly larger head-to-body ratio around 6.5 heads, rounded soft facial contour, large clear eyes, "
             "small chin; styling is doll-like and clean rather than childish",
             "小巧身形、微大的头身比、圆润轮廓与大眼，妆造偏向娃娃感的干净"),
            ("cs_juvenile", "幼态",
             "youthful facial architecture on an adult body: full rounded cheeks, short lower face, "
             "soft jaw with no hard angle, low nose bridge, wide eye spacing, dewy bare-looking makeup",
             "成人体态配年轻面部结构：饱满脸颊、下庭偏短、柔和下颌、山根偏低、眼距略宽、水光淡妆"),
            ("cs_girl", "少女",
             "young woman just past adolescence: slender and slightly unformed frame, light muscle tone, "
             "clear skin with visible fine texture, light natural makeup, hair worn loose or in a simple tie",
             "刚成年的纤细身形、肌肉线条浅、皮肤通透、淡妆、发型蓬松随意"),
            ("cs_young_mature", "轻熟女",
             "mid-twenties to early thirties: balanced figure with defined waist, composed expression, "
             "refined but not heavy makeup, tailored clothing with clean lines",
             "二十五到三十出头、腰线明确、神情沉稳、精致但不浓的妆、剪裁利落的服装"),
            ("cs_oneesan", "御姐",
             "tall self-possessed woman: long limbs, high waistline, sharp shoulder line, "
             "defined cheekbones and jaw, dark or deep-toned makeup with a strong lip, upright posture",
             "高挑长肢、腰线高、肩线利落、骨相立体、深色系浓唇、姿态挺拔"),
            ("cs_married_young", "少妇",
             "married woman in her late twenties to thirties: softer fuller figure, warm expression with "
             "a hint of fatigue, elegant everyday makeup, clothing that is feminine and well kept",
             "三十前后的丰润体态、温和带一点倦意的神情、精致日常妆、feminine 且保养得当的衣着"),
            ("cs_mature", "熟女",
             "fully mature woman in her late thirties and beyond: confident full figure, visible grace, "
             "refined skin with real texture, sophisticated makeup, luxurious fabric",
             "成熟丰盈的体态、从容的气质、有真实质感的皮肤、精致妆容、高级面料"),
        ],
    },
    {
        "key": "role",
        "zh": "身份感",
        "en": "social role",
        "subs": [
            ("cs_wife", "人妻",
             "married woman: modest elegant styling, a wedding band as the single telling accessory, "
             "composed gentle expression, clothing that is soft and well cut rather than revealing",
             "端庄温婉的装扮、婚戒作为关键配饰、神情柔和、剪裁柔和的衣着"),
            ("cs_hotmom", "辣妈",
             "mother with a trained figure: flat stomach, defined waist and hips, confident posture, "
             "body-conscious but tasteful clothing, grooming that is clearly maintained",
             "锻炼过的身材、平坦小腹与明确腰臀、自信体态、贴身但得体的衣着"),
            ("cs_bigsister", "大姐姐",
             "older-sister presence: taller than the viewer, relaxed protective stance, "
             "warm confident smile, casual elegant clothing with the sleeves pushed up",
             "高于视线的身形、放松的护持姿态、温暖自信的笑、袖子挽起的随性优雅"),
        ],
    },
    {
        "key": "sweet",
        "zh": "甜美系",
        "en": "sweet register",
        "subs": [
            ("cs_sweet", "甜妹",
             "sweet register: rounded soft features, upward mouth corners, bright open expression, "
             "warm pink and cream palette, light frilly detail",
             "圆润柔和的五官、上扬嘴角、明亮开朗的表情、粉与奶白的暖调、轻量花边细节"),
            ("cs_soft", "软妹",
             "soft register: low muscle tone, sloping shoulders, yielding posture, "
             "muted pastel palette, loose soft fabric that drapes rather than holds shape",
             "肌肉放松、溜肩、姿态柔顺、柔和的低饱和色、垂坠感强的软面料"),
            ("cs_first_love", "初恋感",
             "first-love register: bare-faced honest makeup, slight flush on the cheeks, "
             "unstyled hair with a few loose strands, plain white cotton, remembered rather than posed",
             "近乎素颜的干净妆、脸颊微红、没有做造型的头发、纯白棉质、像被记住的瞬间"),
            ("cs_white_flower", "小白花",
             "innocent fragile register: pale skin, thin frame, downcast or tentative gaze, "
             "white and pale-blue palette, delicate small-scale detail, soft diffused light",
             "偏白的皮肤、纤细身形、略微低垂的目光、白与浅蓝、精细小巧的细节、柔和漫射光"),
        ],
    },
    {
        "key": "calm",
        "zh": "清雅系",
        "en": "quiet register",
        "subs": [
            ("cs_pure", "清纯系",
             "pure clean register: even skin, minimal makeup with clear brows and bare lips, "
             "neat simple clothing with no ornament, neutral bright light",
             "均匀肤色、极简妆容（清晰眉形与裸色唇）、整洁无饰的衣着、中性明亮的光"),
            ("cs_gentle", "温柔系",
             "gentle register: soft eye shape with slightly lowered lids, relaxed mouth, "
             "warm neutral palette, cashmere and silk textures, soft window light",
             "柔和眼型与微垂眼睑、放松的唇、暖中性色、羊绒与丝绸质感、柔和窗光"),
            ("cs_intellectual", "知性",
             "intellectual register: defined brow bone, steady gaze behind thin frames, "
             "structured tailoring, monochrome palette, upright seated or standing posture",
             "眉骨清晰、细框眼镜后稳定的目光、结构感剪裁、单色系配色、挺直坐姿或站姿"),
            ("cs_cold", "清冷",
             "cool distant register: sharp facial planes, straight unsmiling mouth, "
             "flat even light with cool cast, monochrome or deep cool palette, minimal jewellery",
             "锐利的面部转折、平直不笑的唇、冷调平光、单色或深冷色、极少饰品"),
        ],
    },
    {
        "key": "strong",
        "zh": "强势系",
        "en": "assertive register",
        "subs": [
            ("cs_bright", "明艳",
             "striking register: high-contrast features, saturated lip colour, glossy defined hair, "
             "jewel-toned or bright red clothing, strong directional light",
             "高对比五官、饱和唇色、有光泽的成型发型、宝石色或正红衣装、强烈定向光"),
            ("cs_queen", "女王",
             "commanding register: tall upright stance with chin level, hard shoulder line, "
             "structured garment with width at the shoulder, deep saturated colour, low-angle framing",
             "挺拔平视的姿态、硬朗肩线、肩部有体量的结构服装、深饱和色、低角度取景"),
        ],
    },
    {
        "key": "fresh",
        "zh": "自然系",
        "en": "natural register",
        "subs": [
            ("cs_neighbor", "邻家",
             "approachable register: ordinary pleasant proportions, easy natural expression, "
             "everyday clothing that fits without styling, soft afternoon light",
             "亲和的比例、自然轻松的表情、日常合身但不过度造型的衣着、午后柔光"),
            ("cs_genki", "元气",
             "energetic register: mid-motion pose, wide bright eyes, open laughing mouth, "
             "sporty casual clothing, high-key daylight, visible movement in hair and fabric",
             "动作进行中的姿态、明亮大眼、开口笑、运动休闲装、高调日光、发丝与衣料有明显动势"),
            ("cs_sporty", "运动系",
             "athletic register: trained muscle definition, sun-warmed skin, "
             "technical sportswear and sneakers, outdoor daylight, sweat sheen on the skin",
             "有训练痕迹的肌肉、日照感的皮肤、机能运动装与球鞋、户外日光、皮肤有汗光"),
        ],
    },
    {
        "key": "trend",
        "zh": "潮流系",
        "en": "trend register",
        "subs": [
            ("cs_hot", "辣妹",
             "hot register: tanned or warm-toned skin, body-conscious fit, midriff or leg exposed, "
             "bold makeup with strong liner, statement accessories, direct confident gaze",
             "小麦或暖调皮肤、贴身材质、露出腰腹或腿部、浓眼线与醒目配饰、直视镜头"),
            ("cs_pure_desire", "纯欲",
             "pure-desire register: clean innocent makeup contrasting with a revealing cut, "
             "wet-look skin highlight, soft focus, the contrast itself is the point",
             "干净无辜的妆面配暴露剪裁、湿润高光的皮肤、柔焦、反差本身就是重点"),
            ("cs_sweetcool", "甜酷",
             "sweet-cool register: soft features with hard styling, pastel garment cut with "
             "black leather or metal hardware, one sweet element and one severe element",
             "柔和五官配硬朗造型、粉彩衣装配黑色皮革或金属件、甜与酷各占一半"),
            ("cs_salty", "盐系",
             "salty register: understated features, flat muted palette of grey beige and navy, "
             "loose unstructured clothing, no visible makeup, overcast light",
             "不张扬的五官、灰米藏青的低饱和配色、宽松无结构的衣着、几乎看不出妆、阴天光"),
        ],
    },
    {
        "key": "art",
        "zh": "文艺系",
        "en": "arty register",
        "subs": [
            ("cs_literary", "文艺系",
             "literary register: thoughtful half-lidded gaze, unstyled long hair, "
             "linen and knit textures, bookish props, warm side light with dust in the air",
             "若有所思的半垂目光、未造型的长发、亚麻与针织质感、书本类道具、暖侧光带浮尘"),
            ("cs_mori", "森系",
             "mori register: layered natural-fibre clothing in moss beige and forest green, "
             "soft silhouette with no waist emphasis, bare face, dappled woodland light",
             "苔米与林绿的多层天然纤维衣着、不强调腰线的宽松轮廓、素颜、林间斑驳光"),
        ],
    },
    {
        "key": "animal",
        "zh": "动物系",
        "en": "animal archetype",
        "subs": [
            ("cs_cat", "猫系",
             "cat archetype: upturned outer eye corners, small mouth, aloof watchful expression, "
             "sleek hair, supple languid posture, cool-toned palette",
             "外眼角上扬、小嘴、疏离而警觉的神情、顺滑发型、柔软慵懒的姿态、冷调"),
            ("cs_dog", "犬系",
             "dog archetype: round eyes with visible lower lid, open friendly expression, "
             "soft floppy hair, eager forward-leaning posture, warm palette",
             "圆眼与明显下眼睑、开朗友善的表情、柔软垂顺的发、前倾的热情姿态、暖调"),
            ("cs_fox", "狐狸系",
             "fox archetype: long narrow eyes with a sharp upward tilt, pointed chin, "
             "knowing half-smile, sleek dark hair with a pointed hairline, sharp shoulder line",
             "细长上挑的眼、尖下巴、了然的半笑、深色顺滑发与尖发际线、利落肩线"),
        ],
    },
    {
        "key": "aura",
        "zh": "氛围系",
        "en": "atmosphere register",
        "subs": [
            ("cs_aura", "氛围感",
             "atmosphere-led register: the face is partly obscured by light, hair or framing; "
             "shallow focus, strong environmental colour cast, the mood carries the image",
             "面部被光、发丝或构图部分遮挡、浅景深、强烈的环境色、情绪主导画面"),
        ],
    },
]

SUB_INDEX: dict[str, tuple[dict, dict]] = {}
for _f in CHAR_TREE:
    for _s in _f["subs"]:
        SUB_INDEX[_s[0]] = (_f, {
            "key": _s[0], "zh": _s[1], "en": _s[2], "zh_note": _s[3],
        })

FAMILY_BRIEF = {
    "age": "a specific age impression that drives proportion and makeup weight",
    "role": "a social role that drives styling restraint and posture",
    "sweet": "a sweet visual register, soft features and warm palette",
    "calm": "a quiet visual register, restrained makeup and cool light",
    "strong": "an assertive visual register, hard lines and saturated colour",
    "fresh": "a natural everyday register, easy posture and daylight",
    "trend": "a trend-led register with deliberate contrast in styling",
    "art": "an arty register, natural fibres and thoughtful light",
    "animal": "an animal archetype carried by eye shape and posture",
    "aura": "an atmosphere-led register where mood outranks the face",
}


def resolve_multi(keys: list[str]) -> tuple[str, str]:
    """Resolve a selection to (label_zh, english_clause).

    Character tags stack the same way style tags do: 御姐 + 猫系 reads as one
    person, and the clause is written so the two descriptors agree rather than
    contradict.
    """
    labels: list[str] = []
    phrases: list[str] = []
    seen_l: set[str] = set()
    seen_p: set[str] = set()

    for k in keys or []:
        if k in SUB_INDEX:
            fam, sub = SUB_INDEX[k]
            lab = f"{fam['zh']}·{sub['zh']}"
            ph = sub["en"]
        else:
            fam = next((c for c in CHAR_TREE if c["key"] == k), None)
            if not fam:
                continue
            lab = fam["zh"]
            ph = FAMILY_BRIEF.get(k, fam["en"])
        if lab not in seen_l:
            labels.append(lab)
            seen_l.add(lab)
        if ph not in seen_p:
            phrases.append(ph)
            seen_p.add(ph)

    if not labels:
        return "不指定", ""
    return " + ".join(labels), ", ".join(phrases)


def as_tree() -> list[dict]:
    return [
        {
            "key": c["key"], "zh": c["zh"], "en": c["en"],
            "subs": [{"key": s[0], "zh": s[1], "en": s[2], "note": s[3]} for s in c["subs"]],
        }
        for c in CHAR_TREE
    ]


def total_nodes() -> int:
    return len(CHAR_TREE) + len(SUB_INDEX)
