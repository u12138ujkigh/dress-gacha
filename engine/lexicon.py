# -*- coding: utf-8 -*-
"""Lexicon for the dress gacha: four intensity tiers x sixteen style families.

Design: a style family owns *what she wears and where she is*; the tier owns *how
much skin and what kind of scene*. Keeping those axes apart is what lets any style
be drawn at any intensity without writing 64 hand-made blocks, and it keeps the
language consistent enough that a batch of draws still reads as one shoot.
"""
from __future__ import annotations

TIERS = ["normal", "edgy", "nude", "explicit"]

TIER_META = {
    "normal": {
        "zh": "正常版",
        "en": "Normal",
        "color": "#6ee7ff",
        "desc": "完整着装，可露肩露背，无性暗示",
    },
    "edgy": {
        "zh": "擦边版",
        "en": "Edgy",
        "color": "#ffc94d",
        "desc": "高暴露剪裁、薄透贴身、走光边缘，不露点",
    },
    "nude": {
        "zh": "裸露版",
        "en": "Nude",
        "color": "#ff7ab6",
        "desc": "露点、半遮半掩、全裸",
    },
    "explicit": {
        "zh": "色情版",
        "en": "Explicit",
        "color": "#ff5a5a",
        "desc": "裸露之上叠加性道具与性元素（乳钉、项圈、束缚、玩具）",
    },
}

# ---------------------------------------------------------------- style families
# zh / garment material / where it is shot / how the body reads
STYLES: dict[str, dict] = {
    "satin_gown": {
        "zh": "缎面礼服",
        "material": "lustrous heavy satin with soft liquid highlights",
        "scenes": [
            "minimal seamless light-grey studio backdrop, faint floor reflection",
            "marble hotel lobby at dusk, warm chandeliers bokeh",
            "empty theatre stage with velvet curtains, single spotlight",
            "rooftop terrace at blue hour, city lights far behind",
        ],
        "bodies": [
            "slender elegant figure, long legs, fair porcelain skin",
            "soft hourglass figure, defined waist, graceful carriage",
        ],
        "palette": ["silver-white and champagne", "deep burgundy and gold", "midnight navy and pearl"],
    },
    "wedding": {
        "zh": "婚纱",
        "material": "ivory mikado and layered tulle with pearl beading",
        "scenes": [
            "bright airy bridal atelier, white curtains diffuse light",
            "old stone chapel interior, sunbeam through stained glass",
            "garden ceremony aisle, blurred white roses",
            "seaside cliff at sunset, wind in the veil",
        ],
        "bodies": [
            "willowy graceful figure, fair skin, poised shoulders",
            "curvy soft figure, cinched waist, romantic presence",
        ],
        "palette": ["ivory and blush pink", "pure white and silver", "champagne and sage green"],
    },
    "cheongsam": {
        "zh": "旗袍",
        "material": "silk brocade qipao with high mandarin collar and side slits",
        "scenes": [
            "old Shanghai lane at night, wet stone, neon reflections",
            "lacquered teahouse interior, paper lanterns, wooden lattice",
            "art-deco hotel corridor, brass and dark wood",
            "rain-streaked window seat, city blur outside",
        ],
        "bodies": [
            "willowy figure with long neck and slim waist",
            "curvy figure, pronounced hip-to-waist line, smooth skin",
        ],
        "palette": ["deep emerald and gold thread", "crimson and black", "ink blue and silver"],
    },
    "hanfu": {
        "zh": "古风仙侠",
        "material": "layered silk hanfu with flowing wide sleeves and embroidered hems",
        "scenes": [
            "ancient courtyard at night, red lanterns, drifting mist",
            "bamboo grove with dappled moonlight",
            "moonlit pavilion over a still lake, lotus leaves",
            "candle-lit wooden chamber, carved screen, incense smoke",
        ],
        "bodies": [
            "delicate slender figure, jade-like skin, long black hair",
            "soft graceful figure, narrow waist, flowing silhouette",
        ],
        "palette": ["moon white and pale gold", "vermilion and ink black", "celadon green and silver"],
    },
    "office": {
        "zh": "职场OL",
        "material": "tailored office wear, crisp blouse and pencil skirt",
        "scenes": [
            "modern glass office at night, city bokeh through windows",
            "empty meeting room, long table, cold fluorescent and one warm lamp",
            "executive elevator lobby, brushed steel and marble",
            "hotel business suite desk, laptop glow",
        ],
        "bodies": [
            "slim professional figure, long legs in stockings",
            "curvy figure in a fitted skirt, confident stance",
        ],
        "palette": ["charcoal and ivory", "navy and camel", "black and deep red"],
    },
    "nurse": {
        "zh": "护士",
        "material": "white medical uniform, soft cotton, fitted at the waist",
        "scenes": [
            "clean clinical room, soft window light, pale green walls",
            "night shift corridor, dim warm lamps",
            "pharmacy shelf aisle, glass and steel",
            "small staff room, locker and folded linen",
        ],
        "bodies": [
            "slim figure, neat posture, fair skin",
            "soft curvy figure, gentle presence",
        ],
        "palette": ["white and mint", "white and pale pink", "white and navy trim"],
    },
    "stewardess": {
        "zh": "空姐",
        "material": "fitted airline uniform with silk scarf and pencil skirt",
        "scenes": [
            "aircraft cabin aisle, warm overhead light, seats blurred",
            "airport gate at dawn, glass wall, runway beyond",
            "hotel room near the airport, curtains half drawn",
            "crew lounge, stainless coffee station",
        ],
        "bodies": [
            "tall slim figure, long legs, poised",
            "curvy figure, neat waist, polished look",
        ],
        "palette": ["navy and red scarf", "burgundy and cream", "grey and gold"],
    },
    "teacher": {
        "zh": "教师",
        "material": "conservative blouse with cardigan and pleated skirt",
        "scenes": [
            "empty classroom after hours, late sun on desks",
            "library stacks, warm reading lamps",
            "faculty office, books and papers",
            "blackboard wall, chalk dust in a light beam",
        ],
        "bodies": [
            "slim figure, gentle posture, glasses",
            "soft figure, modest but shapely",
        ],
        "palette": ["camel and cream", "grey and burgundy", "olive and ivory"],
    },
    "swimsuit": {
        "zh": "泳装",
        "material": "high-cut swimwear with wet sheen",
        "scenes": [
            "infinity pool edge at golden hour, water reflections",
            "tropical beach, turquoise water, soft sand",
            "indoor pool, tiled wall, rippling caustics",
            "cliffside hot spring, steam and dusk",
        ],
        "bodies": [
            "athletic toned figure, sun-kissed skin, water droplets",
            "curvy figure, soft hips, wet skin highlights",
        ],
        "palette": ["turquoise and white", "black and gold", "coral and cream"],
    },
    "lingerie": {
        "zh": "情趣内衣",
        "material": "delicate lace and sheer mesh lingerie",
        "scenes": [
            "bedroom with rumpled white linen, morning light",
            "dark hotel room, single warm lamp",
            "dressing room mirror, soft bulbs",
            "velvet chaise in a dim boudoir",
        ],
        "bodies": [
            "slender figure, smooth skin, delicate collarbone",
            "curvy figure, full hips, soft waist",
        ],
        "palette": ["black lace and candlelight", "ivory lace and rose", "deep red and gold"],
    },
    "lolita": {
        "zh": "洛丽塔",
        "material": "bell-shaped lolita dress with petticoat, ribbons and lace trim",
        "scenes": [
            "vintage tea room, floral wallpaper, porcelain cups",
            "sunlit conservatory, ferns and iron frame",
            "old bookshop corner, dusty light",
            "rose garden arbour, soft afternoon haze",
        ],
        "bodies": [
            "petite delicate figure, small waist",
            "soft rounded figure, doll-like proportions",
        ],
        "palette": ["dusty pink and cream", "black and white", "lavender and ivory"],
    },
    "sleepwear": {
        "zh": "睡衣居家",
        "material": "soft silk sleepwear, loose and thin",
        "scenes": [
            "bedroom in early morning, sheer curtains glowing",
            "apartment sofa, warm lamp, rain outside",
            "kitchen at midnight, fridge light",
            "balcony at dawn, city still asleep",
        ],
        "bodies": [
            "slender relaxed figure, messy hair",
            "soft curvy figure, comfortable and unguarded",
        ],
        "palette": ["cream and pale blue", "dusty rose and grey", "white and warm wood"],
    },
    "leather": {
        "zh": "皮衣机车",
        "material": "black leather jacket and tight leather trousers",
        "scenes": [
            "underground garage, cold strip lights, motorcycle",
            "neon-lit alley after rain, steam vents",
            "industrial loft, concrete and steel",
            "night highway shoulder, headlights",
        ],
        "bodies": [
            "toned athletic figure, sharp shoulders",
            "curvy figure in tight leather, strong thighs",
        ],
        "palette": ["black and chrome", "black and blood red", "charcoal and acid green"],
    },
    "sportswear": {
        "zh": "运动装",
        "material": "fitted athletic wear, sports bra and leggings",
        "scenes": [
            "empty gym at night, mirror wall, cold light",
            "running track at dawn, mist on the field",
            "yoga studio, wooden floor, soft window light",
            "locker room bench, tiled wall",
        ],
        "bodies": [
            "athletic lean figure, visible muscle tone, sweat sheen",
            "curvy fit figure, strong thighs, toned stomach",
        ],
        "palette": ["grey and neon yellow", "black and white", "dusty blue and coral"],
    },
    "yukata": {
        "zh": "和服浴衣",
        "material": "light cotton yukata with obi sash",
        "scenes": [
            "ryokan tatami room, shoji screens, summer night",
            "outdoor onsen, steam, stone and lantern",
            "festival street, paper lanterns, crowd bokeh",
            "wooden engawa facing a moss garden",
        ],
        "bodies": [
            "slender figure, long neck, bare shoulders",
            "soft figure, gentle curves under thin cotton",
        ],
        "palette": ["indigo and white", "pale pink and navy", "black and vermilion"],
    },
    "idol_stage": {
        "zh": "舞台偶像",
        "material": "stage costume with sequins, fringe and metallic trim",
        "scenes": [
            "concert stage, beams and haze, crowd lights below",
            "backstage mirror room, bulbs around the frame",
            "rehearsal studio, mirrored wall, cold light",
            "rooftop at night, neon signage",
        ],
        "bodies": [
            "slim dancer figure, long legs, stage presence",
            "curvy figure, confident performance stance",
        ],
        "palette": ["holographic silver and pink", "black and gold sequin", "electric blue and white"],
    },
}

# ---------------------------------------------------------------- garments by tier
# normal = fully dressed; edgy = same garment cut open; nude = removed / see-through
GARMENT: dict[str, dict[str, list[str]]] = {
    "satin_gown": {
        "normal": [
            "off-shoulder satin evening gown with a bandeau neckline and absolutely no shoulder straps, draped cowl bodice, cinched waist with side gathered pleats, floor-length skirt with a modest front slit",
            "one-shoulder satin gown with ruched bodice and soft train, elegant and covered",
            "strapless satin column gown with structured corset waist and long skirt",
        ],
        "edgy": [
            "off-shoulder satin gown with a plunging neckline to the navel, hip-high front slit, no bra",
            "backless satin gown, deep cowl front barely covering, thigh slit, fabric clinging to the body",
            "sheer-panelled satin gown, side cut-outs at the waist, underboob line visible, hip slit",
        ],
        "nude": [
            "the satin gown pulled down to the waist, bare breasts exposed, fabric pooling around the hips",
            "gown discarded on the floor, completely nude, only the satin sash draped across one shoulder",
            "sheer wet-look satin clinging to bare skin, nipples visible through the fabric, gown sliding off",
        ],
        "explicit": [
            "nude on rumpled satin, pierced nipples with silver rings, leather collar around the neck",
            "gown open at the front, bare breasts and shaved pussy exposed, choker and chain leash trailing to the floor",
            "fully nude except bondage ropes across the torso and a satin blindfold, nipples clamped",
        ],
    },
    "wedding": {
        "normal": [
            "ivory wedding gown, illusion neckline with lace overlay, full A-line skirt and long veil",
            "off-shoulder mikado bridal gown, pearl-beaded bodice, cathedral train",
            "high-neck lace wedding dress with buttoned back and long sleeves",
        ],
        "edgy": [
            "wedding gown with a deep plunging neckline and open back, corset lacing, thigh-high slit in the tulle",
            "sheer tulle bridal bodice, visible underboob, low-cut back to the tailbone, fitted hips",
            "strapless bridal gown slipping low, heavy cleavage, slit to the hip, veil trailing",
        ],
        "nude": [
            "wedding gown unzipped and falling from the shoulders, bare breasts and stomach exposed",
            "nude beneath a sheer bridal veil, full body visible through the lace",
            "gown around the waist, topless, holding the bouquet against the chest",
        ],
        "explicit": [
            "nude bride, white garter belt and stockings, pierced nipples, pearl collar with leash",
            "wedding dress bunched at the waist, bare breasts and pussy exposed, nipple clamps and chain",
            "bound with white silk ropes in a bridal veil, nipples pierced, legs spread",
        ],
    },
    "cheongsam": {
        "normal": [
            "silk brocade qipao with high mandarin collar, fitted waist, side slit to the knee",
            "long-sleeved embroidered qipao, frog buttons down the side, modest slit",
            "fitted qipao in deep emerald with gold thread pattern, calf-length",
        ],
        "edgy": [
            "qipao with the slit opened to the hip, collar unbuttoned low, fabric stretched over the bust",
            "sheer silk qipao, no undergarment, slit to the waist, deep V opening at the chest",
            "tight qipao with the front buttons undone to the navel, hip-high slit, bra visible",
        ],
        "nude": [
            "qipao unfastened and sliding off the shoulders, bare breasts and thigh exposed",
            "qipao opened completely at the front, nude beneath, silk falling away",
            "nude with the qipao draped open over the arms, body fully exposed",
        ],
        "explicit": [
            "nude in an open qipao, pierced nipples with gold rings, jade choker and chain",
            "qipao around the elbows, breasts and pussy exposed, silk sash binding the wrists",
            "nude, nipples clamped with jade clamps, red rope harness over the hips",
        ],
    },
    "hanfu": {
        "normal": [
            "layered hanfu with crossed collar, wide flowing sleeves, embroidered sash and long skirt",
            "moon-white hanfu with gold embroidery, high waist tie, trailing ribbons",
            "sheer outer robe over a lined inner dress, elegant and fully covered",
        ],
        "edgy": [
            "hanfu with the collar pulled open to the sternum, sheer outer robe, sash loose, one shoulder bare",
            "wet hanfu clinging to the body, inner dress translucent, skirt slit to the thigh",
            "off-shoulder hanfu, chest wrap barely covering, long skirt open at the side",
        ],
        "nude": [
            "hanfu robe slipped off both shoulders, bare breasts, sash hanging loose at the waist",
            "nude beneath a translucent silk outer robe, body visible through the gauze",
            "inner dress pulled down, topless, long skirt pooled at the feet",
        ],
        "explicit": [
            "nude in an open hanfu robe, pierced nipples with silver rings, red silk cord binding the arms",
            "bare breasts and pussy exposed, jade collar with chain, ribbons tied around the thighs",
            "bound in red silk ropes, nipple clamps with tassels, hanfu open beneath",
        ],
    },
    "office": {
        "normal": [
            "crisp white blouse buttoned high, charcoal pencil skirt, sheer stockings, heels",
            "tailored blazer over a silk camisole, fitted trousers, minimal jewellery",
            "navy office dress with a modest neckline and belted waist",
        ],
        "edgy": [
            "blouse unbuttoned to the sternum, no bra, tight pencil skirt slit at the back, thigh stockings",
            "sheer white blouse over a black bra, skirt hiked high, garter straps visible",
            "blazer only, unbuttoned, bare skin beneath, skirt on the floor",
        ],
        "nude": [
            "blouse open and falling off the shoulders, bare breasts, skirt unzipped",
            "nude except for unbuttoned blouse and thigh-high stockings, body exposed",
            "topless in an open blazer, breasts bare, skirt around the ankles",
        ],
        "explicit": [
            "nude in an open blouse, pierced nipples, leather collar and tie used as a leash",
            "bare breasts and pussy exposed on the office desk, nipple clamps, stockings torn",
            "bound to the chair with a necktie, nude, nipples pierced, legs spread",
        ],
    },
    "nurse": {
        "normal": [
            "white nurse uniform dress, buttoned front, cap, soft cotton, knee length",
            "white scrub top and trousers, ID badge, practical and covered",
            "retro nurse dress with apron and white stockings",
        ],
        "edgy": [
            "nurse dress unbuttoned low, white lace bra visible, skirt short, thigh stockings",
            "sheer white uniform, no bra, buttons open to the waist",
            "uniform top only, bare legs, stockings and garter",
        ],
        "nude": [
            "nurse dress open at the front, bare breasts exposed, cap still on",
            "nude with the uniform hanging open, stethoscope around the neck",
            "topless in an open uniform, white stockings, body fully visible",
        ],
        "explicit": [
            "nude nurse, pierced nipples, stethoscope and leather collar, white stockings",
            "bare breasts and pussy exposed, nipple clamps, medical tray with instruments",
            "bound with bandages, nude, nipples pierced, legs spread on the examination table",
        ],
    },
    "stewardess": {
        "normal": [
            "fitted airline uniform, silk scarf at the neck, pencil skirt, heels",
            "navy uniform jacket and skirt, neat hair, polished and covered",
            "uniform blouse with waistcoat and skirt, conservative neckline",
        ],
        "edgy": [
            "uniform blouse open low, no bra, skirt slit high, scarf loose",
            "sheer uniform shirt, visible bra, tight skirt riding up",
            "jacket only over bare skin, skirt unzipped at the back",
        ],
        "nude": [
            "uniform blouse open, bare breasts, skirt dropped to the floor",
            "nude except for the silk scarf and stockings",
            "topless in the open uniform jacket, breasts bare",
        ],
        "explicit": [
            "nude stewardess, pierced nipples, silk scarf used as a leash, stockings",
            "bare breasts and pussy exposed, nipple clamps, seat belt binding the wrists",
            "bound to the cabin seat, nude, nipples pierced, legs spread",
        ],
    },
    "teacher": {
        "normal": [
            "cream blouse with a cardigan, pleated midi skirt, glasses, modest and neat",
            "buttoned shirt and A-line skirt, low heels, book in hand",
            "knit sweater over a collared shirt, long skirt",
        ],
        "edgy": [
            "blouse unbuttoned low, skirt slit high, stockings, cardigan slipping off",
            "sheer blouse over a lace bra, tight skirt, glasses",
            "shirt tied at the waist, bare midriff, skirt unzipped",
        ],
        "nude": [
            "blouse open, bare breasts, skirt around the ankles, glasses still on",
            "nude beneath an open cardigan, body exposed, hair loose",
            "topless with the skirt held against the hips",
        ],
        "explicit": [
            "nude teacher, pierced nipples, glasses, ruler and leather collar",
            "bare breasts and pussy exposed on the desk, nipple clamps, stockings",
            "bound with a necktie, nude, nipples pierced, chalk dust on the skin",
        ],
    },
    "swimsuit": {
        "normal": [
            "one-piece swimsuit with a high neckline and modest cut",
            "high-waisted two-piece with a sporty top",
            "classic swimsuit with a sarong wrap",
        ],
        "edgy": [
            "high-cut one-piece pulled high on the hips, deep V front, side boob",
            "micro bikini, thin strings, barely covering, wet",
            "sheer wet swimsuit clinging to the body, nipples visible through the fabric",
        ],
        "nude": [
            "swimsuit pulled aside, bare breasts exposed, wet skin",
            "topless with the bikini bottoms only, water droplets",
            "fully nude at the water's edge, wet hair, hands behind the head",
        ],
        "explicit": [
            "nude in the water, pierced nipples, bikini strings tied around the wrists",
            "bare breasts and pussy exposed, nipple clamps with chain, wet skin",
            "bound with the bikini strings, nude, nipples pierced, legs spread on the pool edge",
        ],
    },
    "lingerie": {
        "normal": [
            "lace bralette and matching high-waist briefs under a silk robe",
            "full-coverage lace set with a slip dress over it",
            "soft cotton camisole and shorts set",
        ],
        "edgy": [
            "sheer lace bra and thong, garter belt, stockings, robe open",
            "underboob lace bra, tiny briefs, thigh-high stockings",
            "sheer mesh bodysuit, nipples visible, open at the crotch line",
        ],
        "nude": [
            "bra pulled down, bare breasts, briefs only",
            "nude except for stockings and an open robe",
            "topless, lace briefs, body fully exposed",
        ],
        "explicit": [
            "nude in stockings and a garter belt, pierced nipples, leather collar",
            "bare breasts and pussy exposed, nipple clamps and chain, lace pulled aside",
            "bound with silk stockings, nude, nipples pierced, legs spread",
        ],
    },
    "lolita": {
        "normal": [
            "bell-shaped lolita dress with petticoat, lace collar, ribbon bows, knee socks",
            "high-waist lolita dress with puff sleeves and bonnet",
            "classic lolita coordinate with blouse, jumper skirt and tights",
        ],
        "edgy": [
            "lolita dress with the bodice pulled low, petticoat showing, stockings and garter",
            "sheer lace lolita blouse, no bra, short skirt flipped up",
            "corset laced tight, skirt lifted, thigh-highs",
        ],
        "nude": [
            "lolita dress unfastened and falling, bare breasts, petticoat at the waist",
            "nude beneath sheer lace, bonnet still on",
            "topless with the skirt and petticoat pooled around the feet",
        ],
        "explicit": [
            "nude in lace stockings and a ribbon collar, pierced nipples, ribbon binding the wrists",
            "bare breasts and pussy exposed, nipple clamps with bows, petticoat on the floor",
            "bound with pink ribbon, nude, nipples pierced, legs spread",
        ],
    },
    "sleepwear": {
        "normal": [
            "soft silk pajama set, long sleeves and trousers, loose and comfortable",
            "cotton nightgown with a modest neckline",
            "oversized shirt and shorts, bare feet",
        ],
        "edgy": [
            "thin silk camisole and shorts, no bra, fabric clinging",
            "sheer nightgown, thin straps, thigh visible",
            "oversized shirt unbuttoned, bare legs, underwear visible",
        ],
        "nude": [
            "camisole pulled down, bare breasts, shorts on the floor",
            "nude under a thin sheet, one leg out",
            "topless in bed, hair messy, morning light",
        ],
        "explicit": [
            "nude in bed, pierced nipples, leather collar, sheets tangled",
            "bare breasts and pussy exposed, nipple clamps, wrists bound to the headboard",
            "bound with a silk sash, nude, nipples pierced, legs spread on the sheets",
        ],
    },
    "leather": {
        "normal": [
            "black leather jacket over a t-shirt, tight leather trousers, boots",
            "leather biker jacket, jeans, gloves",
            "fitted leather coat with a high collar",
        ],
        "edgy": [
            "leather jacket open over a bare chest, no bra, leather trousers unzipped",
            "leather harness over bare skin, tight leather skirt",
            "zipped leather top open to the navel, tight leather pants",
        ],
        "nude": [
            "leather jacket open, bare breasts, leather trousers at the knees",
            "nude except for the leather jacket and boots",
            "topless in an open leather jacket, breasts exposed",
        ],
        "explicit": [
            "nude in a leather harness, pierced nipples with rings, studded collar and chain",
            "bare breasts and pussy exposed, leather cuffs and nipple clamps",
            "bound in leather straps, nude, nipples pierced, legs spread on the motorcycle",
        ],
    },
    "sportswear": {
        "normal": [
            "sports bra and full-length leggings, trainers, athletic and covered",
            "zip-up track jacket and shorts, sporty",
            "tank top and running shorts, practical",
        ],
        "edgy": [
            "sports bra only, bare midriff, leggings pulled low on the hips",
            "cropped tank top, no bra, leggings with a camel toe line",
            "sheer athletic top, sweat-soaked, clinging to the body",
        ],
        "nude": [
            "sports bra pulled up, bare breasts, sweat on the skin",
            "nude except for leggings around the ankles",
            "topless after training, breasts bare, towel around the neck",
        ],
        "explicit": [
            "nude after training, pierced nipples, leather collar, sweat sheen",
            "bare breasts and pussy exposed on the gym bench, nipple clamps",
            "bound with resistance bands, nude, nipples pierced, legs spread",
        ],
    },
    "yukata": {
        "normal": [
            "cotton yukata with an obi sash, modest and fully wrapped",
            "indigo yukata with a wide obi and wooden sandals",
            "light yukata loosely tied but covered",
        ],
        "edgy": [
            "yukata slipped off one shoulder, collar open deep, obi loose",
            "wet yukata clinging to the body, fabric translucent",
            "yukata open at the front, no underlayer, sash barely holding",
        ],
        "nude": [
            "yukata fallen from the shoulders, bare breasts, obi at the waist",
            "nude beneath an open yukata, body exposed to the steam",
            "topless with the yukata draped around the elbows",
        ],
        "explicit": [
            "nude in an open yukata, pierced nipples, obi used as a restraint",
            "bare breasts and pussy exposed, jade collar and chain, steam rising",
            "bound with the obi sash, nude, nipples pierced, legs spread on the tatami",
        ],
    },
    "idol_stage": {
        "normal": [
            "sequinned stage costume with a structured bodice and short skirt",
            "metallic stage outfit with fringe and boots",
            "crop jacket and high-waist shorts, performance ready",
        ],
        "edgy": [
            "stage bodice with a deep V and side cut-outs, underboob, micro shorts",
            "sheer stage costume, sequins over bare skin, no bra",
            "fringe top open at the front, high-cut bodysuit",
        ],
        "nude": [
            "stage costume opened, bare breasts, sequins on the floor",
            "nude under coloured stage light, body glistening",
            "topless in an open stage jacket, breasts bare",
        ],
        "explicit": [
            "nude on stage, pierced nipples with rings, studded collar, spotlight",
            "bare breasts and pussy exposed, nipple clamps, microphone stand and chain",
            "bound to the microphone stand, nude, nipples pierced, legs spread",
        ],
    },
}

# ---------------------------------------------------------------- shared dimensions
POSES: dict[str, list[str]] = {
    "normal": [
        "standing straight, hands relaxed at her sides, weight on one leg",
        "turning slightly, looking back over her shoulder, one hand on her hip",
        "walking forward mid-stride, fabric swinging, chin lifted",
        "seated on the edge of a chair, legs crossed, hands folded",
        "leaning against a wall, one knee bent, arms loosely crossed",
    ],
    "edgy": [
        "arching her back, chest pushed forward, one hand sliding down her hip",
        "standing with one leg forward through the slit, hip cocked, chin lowered",
        "leaning back against a wall, shoulders open, one strap sliding down",
        "kneeling on one knee, torso twisted, looking up at the camera",
        "pulling the fabric taut across her body with both hands",
        "sitting with legs apart, leaning forward on her elbows",
    ],
    "nude": [
        "standing fully exposed, arms above her head, body stretched",
        "reclining on her side, one leg bent over the other, hand on her stomach",
        "kneeling upright, thighs apart, hands resting on her thighs",
        "lying on her back, arms above the head, back arched",
        "standing with her back to the camera, looking over her shoulder, hips turned",
        "sitting on the floor, knees drawn up, one arm covering her chest",
    ],
    "explicit": [
        "kneeling with thighs spread wide, hands behind her back, chest pushed out",
        "lying back with legs open, one hand between her thighs",
        "standing, wrists bound above her head, body arched and exposed",
        "on all fours, back arched, looking back at the camera",
        "reclining with legs raised and held open, toes curled",
        "straddling a chair backwards, leaning forward on the backrest",
    ],
}

EXPRESSIONS: dict[str, list[str]] = {
    "normal": [
        "calm composed gaze directly at the camera, lips softly closed",
        "gentle confident smile, eyes relaxed",
        "cool distant expression, chin slightly raised",
        "soft natural look, faint smile, eyes bright",
    ],
    "edgy": [
        "half-lidded sultry gaze, lips parted slightly",
        "biting her lower lip, eyes locked on the camera",
        "defiant look with a faint smirk, eyebrows raised",
        "flushed cheeks, breath visible, eyes glazed",
    ],
    "nude": [
        "vulnerable open gaze, lips parted, cheeks flushed",
        "eyes closed, head tilted back, mouth slightly open",
        "direct unashamed stare, chin down, breathing visible",
        "shy glance away, arms half covering, blush across the chest",
    ],
    "explicit": [
        "mouth open, panting, eyes half closed and unfocused",
        "teary overwhelmed expression, lips swollen, gaze broken",
        "defiant smirk with a flushed face, tongue at the corner of her mouth",
        "head thrown back, eyes squeezed shut, mouth open in a gasp",
    ],
}

ACCESSORIES: dict[str, list[str]] = {
    "normal": [
        "delicate silver drop earrings, thin bracelet",
        "pearl stud earrings and a fine gold necklace",
        "minimal jewellery, small hair clip",
        "statement earrings, no necklace, bare collarbone",
    ],
    "edgy": [
        "layered chains slipping into the neckline, hoop earrings",
        "body chain across the collarbone and waist",
        "choker with a small pendant, statement rings",
        "ear cuff and a thin chain belt",
    ],
    "nude": [
        "only a thin chain across the hips",
        "a single gold necklace against bare skin",
        "small earrings, nothing else",
        "anklet and a hairpin still in place",
    ],
    "explicit": [
        "pierced nipples with silver rings, studded leather collar and chain leash",
        "nipple clamps joined by a chain, leather wrist cuffs",
        "heavy metal collar, nipple rings, chain running down to a belt",
        "bondage harness across the chest, pierced nipples, ankle cuffs",
    ],
}

PROPS: dict[str, list[str]] = {
    "normal": [
        "a small vintage handbag held in one hand",
        "a single long-stemmed rose",
        "a folding fan, half open",
        "a sheer shawl draped over the arms",
    ],
    "edgy": [
        "a glass of champagne, fingers around the stem",
        "a loose silk ribbon trailing from her hand",
        "a wet white shirt held against her body",
        "a mirror reflecting her back",
    ],
    "nude": [
        "a thin bedsheet held loosely against her chest",
        "a translucent curtain between her and the camera",
        "a silk robe open on her shoulders, nothing beneath",
        "water running over her skin",
    ],
    "explicit": [
        "a leather leash clipped to her collar, held taut",
        "a vibrator resting against her thigh",
        "bondage ropes crossing her torso in a harness pattern",
        "a metal spreader bar between her ankles, chain and padlock",
        "a riding crop laid across her collarbone",
        "a leather harness with a ring gag hanging loose at her throat",
    ],
}

LIGHTING = [
    "soft large softbox key from the front-left, gentle fill, subtle rim light",
    "dramatic single-source side light, deep shadows, warm highlights",
    "diffused window light, soft gradients, natural falloff",
    "backlit silhouette with a soft halo, bounce fill from the floor",
    "cool ambient with one warm accent lamp, cinematic contrast",
    "high-key even lighting, no harsh shadow, clean commercial look",
    "low-key chiaroscuro, rim light outlining the body against darkness",
    "golden hour sunlight through a window, long shadows, warm haze",
]

# Studio backdrops: the reference-image look — seamless cyc wall, nothing else.
STUDIO_BACKDROPS = [
    "seamless light grey studio backdrop, absolutely no props, faint floor reflection",
    "seamless white photography cyc wall, soft contact shadow under the feet",
    "seamless warm grey studio paper backdrop, even tone corner to corner",
    "seamless pale cream studio backdrop, gentle gradient toward the floor",
    "seamless charcoal studio backdrop, single soft pool of light behind her",
]

FRAMING = [
    "full body shot, the entire figure from the top of the head to the shoes inside the frame, standing full length, camera at waist height, 85mm lens, shallow depth of field",
    "full length vertical composition, head to toe with a small margin above the head and below the feet, both shoes clearly visible, eye level, 85mm lens",
    "wide full body, whole figure head to toe with negative space above, 35mm lens, environmental portrait",
    "full body, entire standing figure visible including the feet, slight low angle, 105mm lens, compressed background",
    "full body, the whole figure from head to feet fully inside the frame, centred symmetrical composition, 85mm lens",
    "full length, entire body visible with the floor beneath her feet, 50mm lens, generous space around the figure",
]

HAIR = [
    "long black hair in a high bun with crystal hairpins and dangling tassels",
    "loose wavy dark hair falling over one shoulder",
    "sleek wet-look hair slicked back",
    "high ponytail with loose strands framing the face",
    "messy bed hair, strands across the cheek",
    "twin braids pinned up, soft fringe",
    "short bob, sharp and clean",
    "half-up half-down with a silk ribbon",
]

MAKEUP = [
    "clean dewy base, soft red lip, subtle eyeliner",
    "full glam, defined eyes, deep red lip, sculpted cheek",
    "bare-faced natural look, glossy lip, faint blush",
    "smoky eyes, nude glossy lip, highlighted cheekbone",
    "wet-look skin, flushed cheeks, bitten lip tint",
]

IMPERFECTIONS = [
    "natural skin texture with visible pores, faint freckles",
    "subtle sheen of sweat on the collarbone, realistic skin detail",
    "a few loose strands of hair out of place, natural asymmetry",
    "faint pressure marks on the skin from clothing, realistic detail",
    "goosebumps on the arms, cool air, natural texture",
]

QUALITY = (
    "masterpiece, best quality, ultra detailed, photorealistic, "
    "8k, sharp focus, professional photography, natural skin texture, "
    "film grain, cinematic color grading"
)

NEGATIVE_BASE = (
    "lowres, bad anatomy, bad hands, extra fingers, missing fingers, "
    "fused fingers, extra limbs, deformed, disfigured, blurry, "
    "jpeg artifacts, watermark, text, signature, logo, "
    "cartoon, anime, illustration, 3d render, doll-like plastic skin, "
    "oversaturated, harsh flash, cluttered background"
)

NEGATIVE_BY_TIER: dict[str, str] = {
    "normal": "nsfw, nude, topless, nipples, genitals, see-through clothing, ",
    "edgy": "nude, topless, nipples, genitals, ",
    "nude": "censored, mosaic censoring, pixelated, ",
    "explicit": "censored, mosaic censoring, pixelated, ",
}

# ---------------------------------------------------------------- chinese narration
TIER_STORY: dict[str, list[str]] = {
    "normal": [
        "灯下站定，衣料垂出干净的直线，她把重心换到一条腿上，抬眼看向镜头。",
        "快门响起的间隙，她侧过身，肩线在柔光里划出一道弧。",
        "没有多余动作，只是站着，让人看清这套衣服是怎么被撑起来的。",
    ],
    "edgy": [
        "布料被剪开的那一侧露出大片皮肤，她故意把肩沉下去一点，让领口再低一分。",
        "她伸手把裙摆拉平，指尖划过开叉的边缘，眼神却没有离开镜头。",
        "薄透的料子贴着身体，光一斜，轮廓就藏不住了。",
    ],
    "nude": [
        "衣物滑落的声音很轻，她没有去拉，只是把下巴抬起来。",
        "她把手放在胸前又松开，像是在决定要不要遮住什么。",
        "皮肤在光里泛着一点冷意，她抱了抱手臂，还是站直了。",
    ],
    "explicit": [
        "金属扣上的一瞬她抖了一下，随后把脊背挺得更直。",
        "链子被拉紧，她顺着那股力向前倾，呼吸变得很浅。",
        "她跪坐下去，双手背在身后，抬眼看镜头时眼里已经没了退路。",
    ],
}

STYLE_LABEL_ZH = {k: v["zh"] for k, v in STYLES.items()}


def style_tier_matrix() -> dict[str, dict[str, int]]:
    """How many combinations each (style, tier) cell can produce."""
    out = {}
    for s, tiers in GARMENT.items():
        out[s] = {}
        for t, garments in tiers.items():
            n = (len(garments) * len(POSES[t]) * len(EXPRESSIONS[t])
                 * len(ACCESSORIES[t]) * len(PROPS[t])
                 * len(STYLES[s]["scenes"]) * len(LIGHTING) * len(FRAMING)
                 * len(HAIR) * len(MAKEUP) * len(IMPERFECTIONS))
            out[s][t] = n
    return out
