# -*- coding: utf-8 -*-
"""Womenswear taxonomy: 18 primary categories, each with sub-categories.

Sourced from the two reference files (`gemini-code-1794923272513.md` and
`...759.md`). Structure is deliberately one level of nesting:

    CATEGORIES[i]  ->  big class, selectable on its own
      "subs"       ->  small classes, selectable individually
        (key, zh, en_brief, items)

`items` is the Chinese detail list from the reference; it is only sent in API
mode, where the model turns it into English. `en_brief` is what the lexicon mode
uses directly, because that mode must emit English without a model call.
"""
from __future__ import annotations

# (key, zh, en_brief, items)
CATEGORIES: list[dict] = [
    {
        "key": "tops",
        "zh": "常规上装",
        "en": "Tops",
        "brief": (
            "everyday woven and knit tops: a neckline from crew, V, deep U, square, "
            "off-shoulder, sweetheart, mock-neck, cowl, halter or asymmetric; "
            "set-in or dropped shoulders, cropped or oversized, raglan, cap, puff or sleeveless; "
            "crisp shirting, fine-gauge knit, fleece sweatshirt or a camisole layer"
        ),
        "subs": [
            ("tops_tee", "T恤与针织打底",
             "fine cotton jersey tee or knit base layer, crew/V/square/off-shoulder neckline, "
             "cropped or oversized, puff or cap sleeve, garment-dyed cotton with visible rib texture",
             "圆领、V领、大U领、方领、一字领、桃心领、半高领、堆堆领、挂脖领、斜肩领；正肩修身、落肩Oversize、露脐超短款、插肩袖、飞飞袖、泡泡袖、无袖坎肩"),
            ("tops_shirt", "衬衫与雪纺罩衫",
             "crisp cotton poplin or washed silk shirt, double French cuff, cuban or mandarin collar, "
             "pussy-bow tie, leg-of-mutton sleeve, Peter Pan collar, heavy silk satin sheen",
             "法式双叠袖衬衫、牛津纺衬衫、古巴领衬衫、立领衬衫、飘带蝴蝶结衬衫、羊腿袖宫廷衬衫、木耳边立领衬衫、彼得潘娃娃领衬衫、重磅真丝缎面衬衫"),
            ("tops_knit", "毛衣与针织衫",
             "wool or cashmere knit: Fair Isle jacquard, Aran cable, mohair halo, fine ice-silk summer knit, "
             "open crochet, ribbed cardigan or knitted vest, visible stitch structure",
             "费尔岛提花毛衣、阿兰绞花粗棒针毛衣、羊绒打底衫、马海毛慵懒毛衣、冰丝夏薄针织衫、镂空钩花罩衫、针织开衫、针织马甲"),
            ("tops_sweatshirt", "卫衣与运动休闲上衣",
             "brushed fleece sweatshirt, hooded or crew, half-zip stand collar, heavyweight washed cotton, "
             "cropped drawcord hem, ribbed cuffs and hem",
             "连帽套头卫衣、连帽拉链开衫、无帽圆领卫衣、半拉链立领卫衣、水洗做旧重磅卫衣、露腰抽绳卫衣"),
            ("tops_cami", "抹胸与吊带",
             "silk camisole with narrow or wide straps, bustier with boning worn as outerwear, "
             "tube bandeau, halter neck with open back, fine satin strap adjusters",
             "细肩带真丝吊带、宽肩带针织背心、鱼骨紧身胸衣外穿、抹胸裹胸、挂脖露背肚兜式上衣"),
        ],
    },
    {
        "key": "outerwear",
        "zh": "外套与大衣",
        "en": "Outerwear & Coats",
        "brief": (
            "outer layer with real tailoring: shoulder line and padding, lapel shape, closure count, "
            "coat length below the knee or to the ankle, belt and storm flap, "
            "from a cropped biker to a long wool overcoat"
        ),
        "subs": [
            ("out_blazer", "西装外套",
             "tailored blazer: single or double breasted, waist suppressed, shoulder pad thickness stated, "
             "tweed bouclé or linen or wool, patch or welt pockets, working cuff buttons",
             "修身收腰一粒扣西装、双排扣英伦格纹西装、无领小香风粗花呢短外套、垫肩廓形西装、亚麻夏季薄款西装、无袖长款西装马甲"),
            ("out_jacket", "夹克与短外套",
             "biker leather jacket with asymmetric zip, bomber with ribbed collar, washed denim trucker, "
             "varsity with contrast sleeves, multi-pocket utility jacket, corduroy barn coat",
             "斜拉链机车皮衣、立领简约机车皮衣、复古飞行员皮夹克、经典水洗牛仔夹克、短款露腰毛边牛仔衣、MA-1飞行员夹克、美式拼接棒球服、多口袋工装夹克、巴恩风灯芯绒翻领夹克"),
            ("out_coat", "风衣与大衣",
             "trench with gun flap and epaulettes, minimal beltless drape coat, long wool overcoat, "
             "double-faced cashmere robe coat, H-line or X-line silhouette, cocoon shoulder, duffle with toggles, cape",
             "英伦双排扣系带风衣、极简无扣垂感风衣、皮质长款风衣、双面羊绒系带浴袍大衣、H型直筒长款大衣、X型收腰赫本风大衣、茧型落肩大衣、牛角扣学院大衣、斗篷披风大衣"),
            ("out_down", "羽绒服与冬装棉服",
             "down jacket: light channel-quilted, cropped puffer, belted parka with fur hood, "
             "over-knee length, diamond quilting, shearling aviator, faux fur, quilted cotton Chinese-style",
             "轻薄排骨羽绒服、短款面包服、收腰派克羽绒服、过膝超长款羽绒服、菱格绗缝棉服、皮毛一体机车服、环保仿皮草外套、新中式提花加棉袄"),
        ],
    },
    {
        "key": "pants",
        "zh": "下装·裤装",
        "en": "Bottoms - Pants",
        "brief": (
            "trousers with a stated rise and leg line: skinny, straight, wide-leg, mom, bootcut or flare; "
            "denim wash and distressing, front pleats, cargo pockets, elastic cuff, visible stitching"
        ),
        "subs": [
            ("pants_denim", "牛仔裤",
             "denim with a stated cut — skinny, straight, wide-leg, mom, bootcut or flare — "
             "wash level, whiskering, rips, raw hem, low or high rise, copper rivets",
             "紧身铅笔裤、直筒烟管牛仔裤、宽松拖地阔腿牛仔裤、老爹裤、微喇裤、大喇叭裤、低腰工装牛仔裤；水洗做旧、猫须磨白、破洞、毛边裤脚"),
            ("pants_tailored", "休闲与西装长裤",
             "tailored trousers: high-rise wide leg in fluid wool, cropped cigarette, front-pleated, "
             "corduroy straight, linen blend, cargo utility, drawcord harem, overalls",
             "高腰垂感西装阔腿裤、九分烟管通勤裤、前片压褶西装裤、灯芯绒直筒裤、棉麻阔腿裤、多口袋战术工装裤、抽绳哈伦裤、背带长裤"),
            ("pants_sport", "运动与紧身裤",
             "athletic legging or sweatpant: high-rise compression, seamless knit, stirrup hem, "
             "cuffed jogger, side stripe, biker short, elastic waistband",
             "高腰提臀鲨鱼裤、无尴尬线裸感瑜伽裤、踩脚健美裤、束脚加绒运动卫裤、侧条纹校服裤、五分骑行短裤"),
            ("pants_shorts", "女士短裤",
             "shorts: high-rise A-line denim cut-off, rolled cuff, tailored wide-leg, "
             "knee-length Bermuda, pleated skort, leather, visible hem finish",
             "高腰A字牛仔热裤、卷边休闲牛仔短裤、西装高腰阔腿短裤、及膝百慕大中裤、百褶防走光裙裤、皮质短裤"),
        ],
    },
    {
        "key": "skirts",
        "zh": "下装·半身裙",
        "en": "Bottoms - Skirts",
        "brief": (
            "skirt with a stated length and volume: mini to maxi, pleat type and count, "
            "pencil or mermaid line, slit position, petticoat support, fabric drape"
        ),
        "subs": [
            ("skirt_len", "按裙长",
             "skirt length stated precisely: micro mini, above knee, midi calf, tea length, "
             "ankle or floor-sweeping maxi, hem finished clean or raw",
             "超短裙、及膝裙、迷笛中长裙、茶歇长裙、及踝拖地长裙"),
            ("skirt_shape", "按廓形与工艺",
             "skirt silhouette and construction: fine accordion pleats, box pleats, "
             "tiered ruffle cake, straight one-step, high-slit pencil, mermaid with flounce, "
             "A-line, full circle, tulle tutu, high-low tail",
             "细密风琴百褶裙、宽褶学院百褶裙、不规则压褶裙、木耳边蛋糕裙、直筒一步裙、高腰包臀铅笔裙、高开衩包臀裙、鱼尾荷叶边半裙、经典A字半裙、360度大摆伞裙、网纱蓬蓬裙、前短后长燕尾半裙"),
            ("skirt_fabric", "按特色面料",
             "skirt in a signature fabric: bias-cut silk satin with liquid fall, "
             "heavy sequin or bead embroidery, washed denim with slit, PU leather A-line, "
             "Scottish tweed check, ribbed knit bodycon",
             "斜裁真丝缎面半裙、重工亮片珠片半裙、水洗牛仔开衩长裙、PU皮质A字短裙、苏格兰粗花呢格纹裙、针织坑条包臀长裙"),
        ],
    },
    {
        "key": "onepiece",
        "zh": "连体与套装",
        "en": "One-pieces & Sets",
        "brief": (
            "one-piece or matched set, with the waistline height and seaming stated; "
            "dress type from wrap to slip to shirtwaist, jumpsuit with its closure, "
            "co-ord set with the pieces named"
        ),
        "subs": [
            ("one_dress", "连衣裙",
             "dress: wrap tea dress, belted shirtwaist, polo knit, ribbed bodycon, "
             "H-line slip, pinafore, silk slip with cowl, square-neck puff sleeve, "
             "backless tie, boho tassel print, off-shoulder ruffle, babydoll, hooded sweatshirt dress, turtleneck sweater dress",
             "法式V领裹身茶歇裙、收腰系带衬衫裙、Polo运动连衣裙、针织修身长裙、背心H型直筒裙、背带连衣裙、吊带真丝睡衣风长裙、法式方领泡泡袖连衣裙、露背绑带度假长裙、波西米亚流苏印花裙、一字肩荷叶边连衣裙、娃娃裙、连帽卫衣裙、高领毛衣连衣裙"),
            ("one_jumpsuit", "连体裤装",
             "jumpsuit: blazer-collar high-waist wide leg, utility zip front, "
             "strapless or halter formal jumpsuit, denim overall short, floral romper",
             "西装领高腰阔腿连体长裤、工装拉链连体裤、抹胸挂脖礼服连体裤、背带牛仔连体短裤、度假碎花连体短裤"),
            ("one_set", "套装组合",
             "matched set: cropped tweed jacket with skirt, blazer with trousers or shorts, "
             "knit cardigan over camisole, sweatshirt with joggers, mandarin-collar top with skirt",
             "小香风短外套+半裙套装、西装外套+西装裤短裤套装、针织开衫+吊带两件套、运动卫衣+卫裤套装、新中式盘扣上衣+半裙套装"),
        ],
    },
    {
        "key": "intimates",
        "zh": "内衣·家居·贴身",
        "en": "Intimates & Loungewear",
        "brief": (
            "intimate or loungewear layer with its support structure named: "
            "underwire or wireless, cup construction, strap width, band closure, "
            "fabric opacity in denier, sheer mesh panels, lace pattern scale"
        ),
        "subs": [
            ("int_bra", "文胸",
             "bra with construction stated: underwired push-up, wireless jelly-strip support, "
             "French sheer lace triangle bralette, strapless bandeau, front-close, full cup, "
             "silicone pasties; lace scale and strap width visible",
             "钢圈聚拢文胸、无钢圈果冻条软支撑文胸、法式超薄蕾丝三角杯、无肩带抹胸内衣、前扣美背文胸、大胸显小全罩杯文胸、隐形硅胶胸贴"),
            ("int_brief", "女士内裤",
             "briefs: cotton mid-rise, seamless ice-silk one-piece, sheer lace low-rise, "
             "boyshort safety, high-waist shaping, thong or T-back",
             "纯棉中腰三角裤、无痕冰丝一片式内裤、蕾丝透明低腰三角裤、平角安全裤、高腰收腹内裤、丁字裤"),
            ("int_shapewear", "塑身与打底",
             "shapewear: boned corset waist trainer, high-compression bodysuit, "
             "hip-lifting shaping short, anti-static silk slip, thermal brushed base set",
             "鱼骨收腰束腰、连体高弹力塑身衣、提臀塑身短裤、防静电真丝吊带衬裙、德绒发热保暖内衣套装"),
            ("int_sleep", "睡衣与家居服",
             "sleepwear: mulberry silk lapel pajama set, lace-trimmed silk slip nightgown, "
             "modal cotton lounge set, coral fleece thick pajama, waffle robe, wear-out lounge set",
             "桑蚕丝翻领开衫睡衣套装、蕾丝吊带真丝睡裙、莫代尔纯棉家居套装、珊瑚绒法兰绒加厚睡衣、华夫格浴袍、可外穿休闲家居套装"),
            ("int_swim", "泳装与温泉服",
             "swimwear: one-piece with open back, retro high-waist bikini, "
             "triangle string bikini, skirted conservative suit, long-sleeve rash guard, "
             "hot-spring split with small skirt; wet fabric cling and sheen",
             "连体露背三角泳衣、复古高腰分体比基尼、三角系带比基尼、遮肚裙式保守泳衣、长袖防晒冲浪服、温泉分体小裙装"),
            ("int_hosiery", "袜类与丝袜",
             "hosiery by denier: 10D ultra-sheer invisible, 120D velvet opaque, "
             "fleece-lined, lace-top thigh-high, polka-dot or bow jacquard, fishnet, "
             "slouch sock, no-show, athletic crew",
             "0D-15D超薄隐形丝袜、80D-200D天鹅绒打底连裤袜、加绒光腿神器、蕾丝花边大腿过膝袜、波点蝴蝶结提花丝袜、镂空渔网袜、小腿堆堆袜、船袜、运动中筒袜"),
        ],
    },
    {
        "key": "formal",
        "zh": "晚礼服与婚庆",
        "en": "Formal, Evening & Bridal",
        "brief": (
            "formal gown with the bodice construction, skirt volume and train length stated; "
            "beading density, boning, corset lacing, whether the hem clears the floor"
        ),
        "subs": [
            ("frm_gown", "西式晚礼服",
             "evening gown: strapless ball gown with full skirt, one-shoulder silk satin with high slit, "
             "deep-V backless mermaid, hand-beaded sequin, caped queen gown, "
             "three-dimensional floral tulle, little black dress, cocktail dress, tuxedo suit",
             "抹胸大裙摆公主蓬蓬礼服、单肩高开衩真丝缎面礼服、深V露背鱼尾修身礼服、全手工重工钉珠亮片晚礼服、斗篷披肩式女王礼服、立体花朵薄纱仙女礼服、及膝小黑裙、鸡尾酒会小礼服、女士高定吸烟装"),
            ("frm_bridal", "西式婚纱与婚礼周边",
             "bridal gown: cathedral train, off-shoulder mikado, fishtail lace, "
             "light tulle reception dress, minimal satin travel gown, high-low hem; "
             "bridesmaid chiffon convertible, lace-and-feather bridal robe",
             "教堂大拖尾主婚纱、宫廷一字肩缎面婚纱、鱼尾蕾丝修身婚纱、轻盈薄纱出门纱、法式极简缎面旅拍婚纱、前短后长婚纱、伴娘多穿法雪纺长裙、新娘蕾丝羽毛晨袍"),
            ("frm_chinese", "中式婚庆嫁衣",
             "Chinese bridal: dragon-phoenix embroidery on red ground, wide-sleeve xiuhe, "
             "slimmed fishtail xiuhe, Chaozhou three-dimensional gold embroidery, "
             "red silk qipao, mandarin-collar toast dress",
             "龙凤褂、传统宽袖秀禾服、修身改良鱼尾秀禾服、潮绣立体金龙凤秀禾服、正红色真丝改良旗袍、新中式立领盘扣敬酒长裙"),
        ],
    },
    {
        "key": "aesthetic",
        "zh": "风格与美学流派",
        "en": "Fashion Styles & Aesthetics",
        "brief": (
            "an aesthetic direction rather than a single garment: the era and subculture the "
            "whole look belongs to, which decides palette, silhouette and styling together"
        ),
        "subs": [
            ("aes_quiet", "优雅静奢与经典",
             "old-money quiet luxury or French chic or preppy or geek-chic: "
             "restrained palette within three colours, no visible logo, impeccable pressing, "
             "crisp shirt collar, tailored trouser break, single fine jewellery piece",
             "老钱风静奢风、法式慵懒风、英伦学院风、知识分子风"),
            ("aes_retro", "复古时代",
             "period revival: 1990s Hong Kong glamour, American vintage 50s-70s, Y2K millennium pop sick, "
             "the decade decides the shoulder line, waist and hem",
             "90年代港风复古、美式复古、千禧辣妹风"),
            ("aes_modern", "现代个性与甜酷",
             "modern personal style: minimalism, Korean soft clean, mori natural layers, "
             "bohemian, sweet-cool biker, American high street",
             "极简主义、纯欲风韩系温柔风、森系自然风、波西米亚风、甜酷机车风、美式高街风"),
        ],
    },
    {
        "key": "subculture",
        "zh": "三坑与亚文化",
        "en": "Subculture & Alternative",
        "brief": (
            "subculture silhouette: Lolita JSK/OP/SK with a bell petticoat diameter, "
            "JK sailor collar type, hanfu-fusion layers, or goth/steampunk hardware"
        ),
        "subs": [
            ("sub_lolita", "洛丽塔",
             "Lolita: sweet, classic, gothic, Chinese-style or sailor variant; "
             "JSK, OP or SK cut; bell petticoat diameter, ribbon and lace trim count, "
             "bonnet or headdress, OTK socks",
             "甜美洛丽塔(Sweet)、古典洛丽塔(Classical)、哥特洛丽塔(Gothic)、中华风洛丽塔、水手洛丽塔、基佬装王子装；版型分JSK背带裙、OP连衣裙、SK半裙"),
            ("sub_jk", "JK制服",
             "seifuku: sailor collar in Kansai/Kanto/Nagoya/Sapporo cut, or blazer with knit vest; "
             "plaid pleated skirt with wheel or box pleats, tie or bow, loose socks",
             "水手服(关西襟/关东襟/名古屋襟/札幌襟)、西式制服(西装外套+针织马甲+格纹轮褶/箱褶百褶裙+领结领带)"),
            ("sub_hanmod", "日常汉元素与新中式",
             "modern hanfu fusion: cropped flight-sleeve with baidie skirt, "
             "mamian skirt worn over a shirt or tee, mandarin-collar frog-button crop top with jeans, "
             "dark guochao embroidered jacket",
             "改良短款飞机袖+百迭裙、马面裙日常混搭、国风立领盘扣短上衣+牛仔裤、暗黑系国潮刺绣外套"),
            ("sub_alt", "小众先锋亚文化",
             "alternative: jirai-kei or ryousangata, dark goth, steampunk brass and leather, "
             "Harajuku street collage; visible hardware, straps and mixed textures",
             "日系地雷系量产型、暗黑哥特风、蒸汽朋克、原宿街头拼贴风"),
        ],
    },
    {
        "key": "career",
        "zh": "职业装与行业制服",
        "en": "Career & Uniforms",
        "brief": (
            "occupational uniform: the uniform's actual specification, not a costume version — "
            "badge position, epaulettes, collar type, regulation hem length, issued footwear"
        ),
        "subs": [
            ("car_finance", "金融商务与法务",
             "corporate or legal uniform: skirt suit with white shirt, pencil skirt and silk scarf; "
             "executive tailored trouser suit; black barrister robe; judge's bench robe",
             "银行证券女职工套裙、高管定制修身裤装、女律师黑色正装、女法官检察官制式黑袍"),
            ("car_service", "航空铁路与高端服务",
             "service uniform: flight attendant suit or dress with cabin hat and scarf, "
             "rail crew uniform, hotel concierge, estate advisor, luxury boutique uniform, "
             "exhibition qipao",
             "空姐制服、高铁女乘务员制服、星级酒店前台礼仪套裙、置业顾问套装、高奢专柜女导购制服、会展礼仪旗袍礼服"),
            ("car_medical", "医疗医美与科研",
             "medical:医生 white coat over scrubs, nurse dress with cap, "
             "operating-room scrubs, aesthetic-clinic dress, cleanroom coverall; "
             "cotton fabric stiffness, badge and pen in pocket",
             "女医生白大褂、女护士服、手术室洗手衣、医美顾问修身连衣裙、实验室无尘防静电连体服"),
            ("car_food", "餐饮零售与文旅",
             "food service and retail: double-breasted chef jacket with cap, "
             "half apron over shirt, chain-store polo, tour guide uniform",
             "女厨师双排扣工装与厨师帽、咖啡店西餐厅半身围裙制服、连锁茶饮POLO衫工装、景区女导游制服"),
            ("car_military", "军警与公共执法",
             "uniformed service: police dress or duty or field uniform, military dress and camouflage, "
             "customs and tax and bailiff uniform, firefighter rescue gear; "
             "rank insignia, epaulette, duty belt",
             "女警察常服执勤服作训服、女军人礼服常服迷彩作训服、海关税务法警女性制式制服、女消防员抢险救援服常服"),
        ],
    },
    {
        "key": "historical",
        "zh": "古装与民族服饰",
        "en": "Historical & Ethnic",
        "brief": (
            "historically grounded dress: keep the era's actual construction — collar direction, "
            "waist placement, sleeve width and skirt structure are period facts, not styling choices"
        ),
        "subs": [
            ("his_preqin", "先秦与秦汉",
             "pre-Qin and Han: quju deep robe with wrapped front, zhiju straight robe, "
             "cross-collar ruqun, zaju with trailing streamers",
             "曲裾深衣、直裾深衣、汉代交领襦裙、杂裾垂髾服"),
            ("his_weijin", "魏晋南北朝",
             "Wei-Jin: large-sleeve shan over intercolour skirt, Jin-cut cross-collar ruqun, "
             "half-sleeve ruqun",
             "大袖衫+间色裙、晋制交领襦裙、半臂襦裙"),
            ("his_tang", "隋唐五代",
             "Tang: qixiong high-waist ruqun, qiyao ruqun, tan-collar half sleeve with intercolour skirt, "
             "large-sleeve shan with silk stole, hufu foreign dress with striped trousers and boots, "
             "round-collar robe",
             "齐胸衫裙、齐腰襦裙、坦领半臂+间色裙、大袖衫+披帛、胡服、唐圆领袍"),
            ("his_song", "宋代",
             "Song: beizi over a chest wrap with songku, baidie or sanjian or xuanqun skirt, "
             "straight-collar parallel-front long shan, huiyi robe with phoenix crown",
             "宋制褙子+抹胸+宋裤、百迭裙三裥裙旋裙、直领对襟长衫、宋代袆衣与凤冠霞帔"),
            ("his_liao", "辽金元",
             "Liao-Jin-Yuan: Khitan or Jurchen narrow-sleeve cross-collar long robe, "
             "Mongol zhishun robe, gugu crown with noblewoman dress",
             "契丹女真窄袖交领长袍、蒙古族质孙服曳撒、顾姑冠贵妇华服"),
            ("his_ming", "明代",
             "Ming: stand-collar diagonal-front long ao with mamian skirt, "
             "upright-collar large-front shan with pleated skirt, square-collar parallel-front bijia, "
             "daopao, phoenix crown",
             "立领斜襟长袄+马面裙、竖领大襟衫+百褶裙、方领对襟半臂比甲、道袍直身、明代凤冠霞帔"),
            ("his_qing", "清代与民国",
             "Qing and Republican: Manchu qizhuang with dalachi headdress and platform shoes, "
             "Qing Han woman's aoqun, Shanghai modified qipao, Republican student dress",
             "满族旗装大拉翅旗头+花盆底鞋、清代汉女袄裙、民国海派改良旗袍、民国女学生文明新装"),
            ("his_ethnic", "中国少数民族女装",
             "Chinese ethnic minority dress: Tibetan chuba with apron, Miao pleated skirt with heavy silver, "
             "Uyghur atlas silk dress with embroidered cap, Dai short jacket and tube skirt, "
             "Korean chogori, Yi pleated skirt and felt cape, Mongol edged robe and vest",
             "藏族藏袍与邦典围裙、苗族百褶裙与重工银饰盛装、维吾尔族艾德莱斯绸连衣裙与朵帕花帽、傣族修身短衣+筒裙、朝鲜族赤古里裙、彝族百褶长裙与披毡、蒙古族镶边立领长袍与坎肩"),
            ("his_world", "世界各国传统女装",
             "world traditional dress: kimono in furisode or houmongi or yukata, hanbok chima jeogori, "
             "sari or lehenga, ao dai, Thai silk tube skirt, medieval court gown, renaissance square neck, "
             "rococo pannier lace, Victorian high-collar corset gown",
             "日本和服振袖留袖访问着小纹浴衣、韩国韩服赤古里裙、印度纱丽旁遮普服Lehenga、越南奥黛、泰丝筒裙礼服、欧洲中世纪宫廷长裙、文艺复兴方领礼服、洛可可大裙撑蕾丝礼服、维多利亚高领紧身胸衣长裙"),
        ],
    },
    {
        "key": "activewear",
        "zh": "运动与户外功能服",
        "en": "Activewear & Outdoor",
        "brief": (
            "technical sportswear whose function is visible: support structure, seam placement, "
            "membrane and coating, seam-sealed zips, reflective print, how the fabric behaves wet"
        ),
        "subs": [
            ("act_indoor", "室内健身与球类",
             "gym wear: high-impact shock-absorbing racerback sports bra, low-impact thin-strap yoga bra, "
             "squat-proof seamless legging, one-piece training romper, ballet cross-strap cover-up, "
             "tennis or golf pleated skirt",
             "高强度防震工字背运动内衣、低强度细肩带瑜伽文胸、无尴尬线裸感瑜伽裤、无缝针织健身连体短裤、芭蕾风交叉绑带健身罩衫、网球高尔夫百褶运动短裙"),
            ("act_snowwater", "冰雪与水上专业运动",
             "snow and water sports: relaxed waterproof snow jacket, fitted one-piece ski suit, "
             "bib snow pants, fleece midlayer, long-sleeve rash guard, sharkskin racing swimsuit, wetsuit",
             "单板宽松防水滑雪服、双板修身连体滑雪服、防水背带滑雪裤、防寒抓绒中间层、长袖防晒冲浪连体泳衣、鲨鱼皮竞速泳衣、潜水湿衣"),
            ("act_outdoor", "户外徒步越野与跑步",
             "outdoor shell: three-layer GORE-TEX hardshell, light windproof softshell, "
             "UPF50 sun hoodie, quick-dry tee, convertible hiking trouser, "
             "ultralight reflective running vest, high-fill-power down jacket",
             "GORE-TEX三层压胶防水硬壳冲锋衣、轻量防风软壳夹克、UPF50冰丝防晒皮肤风衣、户外速干T恤、可拆卸徒步速干裤、越野跑超轻反光背心、极寒高蓬松度鹅绒羽绒服"),
        ],
    },
    {
        "key": "specialty",
        "zh": "特殊时期与特定人群",
        "en": "Specialty & Age-Segmented",
        "brief": (
            "cut built for a real body stage or age: maternity panel and nursing access, "
            "school uniform regulation, plus-size proportion correction, senior comfort fabrics"
        ),
        "subs": [
            ("sp_maternity", "孕产期与哺乳期",
             "maternity: 360-degree stretch belly panel jean, loose A-line babydoll dress, "
             "radiation-shield pinafore, side-zip or lift-front nursing top, front-button cotton confinement set",
             "高弹力托腹牛仔裤打底裤、宽松A字娃娃款孕妇连衣裙、防辐射孕妇背带裙、侧开拉链上掀式隐形哺乳上衣、纯棉前开扣月子服套装"),
            ("sp_teen", "少女与学生",
             "student: regulation sports school uniform set, preppy knit cardigan with plaid skirt, "
             "sweet puff-sleeve floral dress",
             "初高中制式运动校服套装、学院风针织开衫+格纹短裙、甜美泡泡袖碎花连衣裙"),
            ("sp_plus", "大码微胖",
             "plus-size: high-waist V-neck French wrap tea dress, fluid wide-leg tailored trouser, "
             "A-line hip-covering midi skirt, slim-look bootcut jean, oversized midi trench",
             "高腰V领法式收腰茶歇裙、垂感高腰阔腿西装裤、A字遮胯中长半身裙、微喇显瘦牛仔裤、廓形中长款风衣"),
            ("sp_senior", "中老年优雅",
             "mature: gambiered Guangdong silk print set, pure wool or cashmere cardigan coat, "
             "mandarin-collar jacquard top, relaxed high-waist linen wide-leg set",
             "香云纱真丝印花套装、纯羊毛羊绒开衫外套、新中式立领盘扣提花上衣、宽松舒适高腰棉麻阔腿裤套装"),
        ],
    },
    {
        "key": "eastern_fantasy",
        "zh": "东方幻想与仙侠",
        "en": "Eastern Fantasy & Xianxia",
        "brief": (
            "Eastern fantasy: layered silk and chiffon with visible translucency, several metres of "
            "flowing stole, embroidery motifs drawn from crane and cloud and scale and feather, "
            "jade and pearl and filigree metal"
        ),
        "subs": [
            ("ef_xianxia", "仙侠飘逸风",
             "cultivation sect or celestial: sect disciple uniform in pale white or sky blue or light azure, "
             "cross-collar wide sleeve, jade token; goddess gown in multi-layer gradient silk chiffon, "
             "metres-long gauze stole, pearl fringe bodice, crane and cloud white-gold embroidery",
             "宗门制式弟子服、上仙神女华服"),
            ("ef_demon", "玄幻神女与魔族妖灵",
             "demon and spirit: black-red or purple-gold or ink-blue palette, heavy gold thread "
             "three-dimensional embroidery, high-slit long skirt, carved metal pauldron and corset, "
             "floor-length dark-pattern cloak; fox or flower or snake or feather spirit forms",
             "魔界暗黑神女、妖灵精怪幻化装"),
            ("ef_wuxia", "武侠江湖劲装",
             "wuxia: fitted stand-collar narrow-sleeve fighter's set, leather bracer and wide waist sash, "
             "high-slit split skirt, black or red hooded cloak, bamboo veil hat or conical hat; "
             "or young-lady travelling set with short jacket and mamian skirt and sword",
             "刺客剑客劲装、世家大小姐江湖装"),
            ("ef_dunhuang", "敦煌飞天与西域异域",
             "Dunhuang flying apsara: bare-midriff jewelled bandeau, lantern wide-leg sheer gauze trouser, "
             "layered gold yingluo bead chains, vermilion and peacock blue and bright yellow silk streamers, "
             "gold-thread embroidered semi-transparent veil",
             "露腰宝石抹胸+灯笼阔腿透明纱裤、繁复金色璎珞珠串配饰、朱红孔雀蓝明黄撞色丝绸飘带、金丝刺绣半透明面纱舞衣"),
            ("ef_guochao", "新中式国潮幻想",
             "cyber-guochao: traditional cross-collar qixiong structure in reflective technical waterproof fabric, "
             "ink-wash landscape gradient print, metallic prosthetic limb with Suzhou-embroidered qipao",
             "传统交领齐胸结构+反光机能防水面料、水墨山水渐变印花现代礼服、金属机械义肢搭配苏绣旗袍"),
            ("ef_fairy", "仙子",
             "fairy: delicate translucent layered gauze in pale pink, white or soft mint; "
             "butterfly or cicada-wing organza cape; petal-shaped hem with drifting ribbon tails; "
             "small blossoms and dewdrop crystal beads scattered over the bodice; "
             "thin gold filigree circlet with dangling tassels; barefoot or translucent silk slippers; "
             "a two to three metre light veil that floats rather than drapes",
             "轻纱薄透藕粉月白薄荷、蝶翼薄纱披帛、花瓣状飘带下摆、胸前散落小朵花枝与露珠水晶、细金丝冠垂流苏、赤足或透纱软履、两三米轻纱飘浮不垂坠"),
            ("ef_goddess", "东方女神",
             "Eastern goddess: majestic floor-length robe in deep vermilion-gold or imperial purple; "
             "wide structured shoulder cape embroidered with sun and cloud; "
             "heavy gold-thread brocade panel down the centre front; "
             "layered jade and gold collar necklace covering the collarbone; "
             "tall ornate crown with phoenix or lotus motif; wide jewelled girdle at the waist; "
             "long trailing hem spreading on the ground; a radial halo of light behind the head",
             "正红鎏金或帝王紫曳地长袍、宽挺肩披绣日月云纹、身前重金线织锦中缝、遮锁骨的层叠玉石金项圈、凤或莲纹高冠、腰间宽镶宝腰带、裙裾铺地、头后放射光晕"),
        ],
    },
    {
        "key": "western_fantasy",
        "zh": "西方奇幻与史诗",
        "en": "Western Fantasy & Mythology",
        "brief": (
            "Western fantasy: leaf-vein metal embroidery, vine silver headpiece, "
            "boned corset under a velvet skirt, light armour plate with engraved scrollwork"
        ),
        "subs": [
            ("wf_elf", "精灵与森林仙子",
             "elf and forest sprite: silver-white or forest-green or champagne, "
             "leaf-vein metal thread embroidery on sheer gown, floor-length trumpet sleeve, "
             "vine silver circlet and shoulder piece; or petal-tiered micro skirt with dragonfly wing, "
             "bark and moss textured bodice",
             "高等精灵礼服、森林小仙子花仙子"),
            ("wf_witch", "女巫与魔法师",
             "witch and mage: wide-brim pointed hat, star-and-tarot embroidered dark robe, "
             "boho distressed lace gown; academy robe with house crest over shirt and tie and pleated skirt; "
             "vampire countess in blood-red and black velvet with exaggerated high collar cape and gothic corset",
             "古典神秘女巫、魔法学院风、吸血鬼女伯爵"),
            ("wf_noble", "中世纪贵族与宫廷",
             "medieval court: gold and silver thread corset with floor-sweeping velvet skirt, "
             "lace trumpet sleeve princess gown, jewelled coronation mantle with ermine trim",
             "金银线重工刺绣紧身胸衣+拖地天鹅绒大摆长裙、蕾丝大喇叭袖公主礼服、镶嵌宝石的王后加冕貂皮滚边大氅"),
            ("wf_valkyrie", "女武神与奇幻轻甲",
             "valkyrie and knight: silver or gold engraved metal chest plate, feathered helm, "
             "white war skirt, red long cape; leather and chainmail fitted battle dress, "
             "metal pauldron and knee guard, dark green hooded ranger cloak",
             "女武神银金雕花金属胸甲+羽毛头盔+白色战裙+红色长披风、女骑士游侠皮革锁子甲紧身战衣+金属护肩护膝+暗绿兜帽披风"),
        ],
    },
    {
        "key": "scifi",
        "zh": "科幻·赛博·未来",
        "en": "Sci-Fi & Cyberpunk",
        "brief": (
            "science fiction: emissive elements and their power source implied by cabling, "
            "technical fabric with stated gloss, exposed seam or hydraulic, "
            "asymmetric cut that reads as engineered rather than tailored"
        ),
        "subs": [
            ("sf_cyberpunk", "赛博朋克与街头机能",
             "cyberpunk: LED strip on translucent PVC trench, multi-pocket tactical chest rig with "
             "strapped cargo trouser, neon colour-block compression top with exposed mech prosthetic, "
             "asymmetric cut, gas mask and tactical goggle",
             "发光LED灯带半透明PVC风衣、多口袋战术机能胸挂马甲+束脚绑带工装裤、霓虹荧光撞色紧身衣+机械义肢外露不对称剪裁、防毒面具与战术护目镜"),
            ("sf_starfleet", "星际宇航与舰队制服",
             "starfleet or space: fitted stand-collar double-breasted captain's uniform with metal epaulette, "
             "white or silver streamlined exoskeleton pressure suit, anti-gravity tight training suit",
             "未来星舰女舰长修身立领双排扣制服+金属肩章、白色银色流线型外骨骼宇航服、反重力太空舱紧身作训服"),
            ("sf_android", "机械姬与仿生人战衣",
             "android: full-coverage metallic liquid-silver latex or patent combat suit, "
             "glowing circuit-board texture skin-tight bodysuit, holographic transparent outer robe, "
             "white armour-panel bionic body shell",
             "全包覆金属光泽液态银乳胶漆皮紧身战斗服、发光电路板纹理科技感贴身战衣、全息投影透明材质外袍、白色装甲拼接仿生人躯体服"),
            ("sf_wasteland", "末世废土生存装",
             "wasteland: torn and sand-worn long cloak, dust goggles and respirator, "
             "armour pieced from tyre and leather and scrap metal, strapped cargo trouser and heavy boot",
             "做旧撕裂磨损风沙大斗篷、防风沙护目镜与呼吸器、废旧轮胎皮革金属碎片拼接护甲装、绑带工装裤与重型马丁靴"),
        ],
    },
    {
        "key": "acg",
        "zh": "二次元·游戏·舞台",
        "en": "ACG, Cosplay & Stage",
        "brief": (
            "staged costume: the trope is legible at a glance, and the material choice "
            "carries it — sequin and vinyl for idol, satin and tulle for magical girl, "
            "embossed leather and metal for game classes"
        ),
        "subs": [
            ("acg_idol", "女团打歌服与偶像舞台",
             "idol stage: sequin and rhinestone cropped top with high-waist pleated micro skirt, "
             "metal waist chain and knee boot; preppy cropped blazer with asymmetric plaid pleats and tie; "
             "underground idol rococo stage dress with tiered skirt, oversized bow, lace glove and mini hat",
             "甜酷女团风、学院打歌服、日系地下偶像洛可可舞台装"),
            ("acg_trope", "经典职业与人设",
             "anime trope: magical girl transform outfit in saturated pink-blue-white with oversized gem bow, "
             "ruffled puff skirt, OTK sock; Japanese maid dress in black-white with ruffled apron and lace headband; "
             "nun habit or battle-nun high-slit version; bunny suit in patent or satin bandeau with ears and cuffs",
             "魔法少女变身装、日系女仆装、修女服、兔女郎舞台装"),
            ("acg_gameclass", "游戏角色职业装",
             "game class: cleric in holy white-gold high-slit robe with sacred-light embroidery and flowing veil; "
             "elemental mage in fire-red or frost-blue asymmetric off-shoulder gown with glowing sigil and "
             "floating stole; shadow assassin in night-black fitted leather with hooded cape and thigh dagger sheath; "
             "Eastern martial artist in high-slit cropped qipao with hand wraps and lantern trouser",
             "神官牧师系、元素法师系、暗影刺客系、东方武道家格斗家"),
        ],
    },
    {
        "key": "roleplay",
        "zh": "情趣制服与角色扮演",
        "en": "Roleplay & Costume Lingerie",
        "brief": (
            "roleplay costume lingerie: the uniform is recognisable by its insignia and cut, "
            "but the garment is rebuilt in sheer or patent or lace; state what is transparent, "
            "what hardware holds it, and where it ends"
        ),
        "subs": [
            ("rp_occupation", "职业扮演制服",
             "occupational roleplay: fitted lace-up white shirt with bodycon micro skirt office secretary; "
             "high-slit sheer nurse dress with cross headband and white stocking; "
             "backless strapped flight-attendant uniform with scarf and pillbox hat; "
             "bare-midriff sailor collar with micro pleated school skirt; "
             "patent zip police uniform with peaked cap and handcuff accessory",
             "紧身系带白衬衫+包臀超短裙OL秘书装、高开衩薄纱护士服+十字发箍+吊带白丝、露背绑带空姐制服+丝巾小帽、露腰海军领水手服+超短百褶学生制服、漆皮拉链女警制服+大檐帽与手铐配饰"),
            ("rp_fantasy", "经典幻想角色情趣装",
             "fantasy roleplay: lace cut-out backless maid dress with ruffled apron and neck ring; "
             "high-slit sheer nun robe with cross veil; patent or velvet bandeau bunny suit with ear headband "
             "and tail; cat-ear plush with bell collar and paw-print bodysuit; "
             "lace dudou with high-slit sheer qipao",
             "蕾丝镂空露背女仆装+荷叶边围裙与颈环、高开衩透视修女袍+十字架头纱、漆皮天鹅绒抹胸兔女郎连体衣+兔耳发箍与尾球、猫娘毛绒耳朵+铃铛项圈+镂空爪印连体衣、蕾丝肚兜+高开衩半透明薄纱旗袍"),
            ("rp_material", "材质与剪裁特种设计",
             "specialist construction: sheer mesh panelled bodysuit, patent or latex high-gloss catsuit, "
             "boned lace garter-belt set, leather and metal O-ring harness with strappy lingerie, "
             "halter backless tie nightgown with open-crotch lace",
             "透视网纱拼接连体衣、漆皮乳胶高光泽紧身束衣、鱼骨蕾丝吊袜带束腰套装、皮革金属环镂空绑带装、挂脖露背系带睡裙与开档蕾丝内衣"),
        ],
    },
]

CATEGORY_KEYS = [c["key"] for c in CATEGORIES]

# Flat index: sub key -> (category, sub dict)
SUB_INDEX: dict[str, tuple[dict, dict]] = {}
for _c in CATEGORIES:
    for _s in _c["subs"]:
        SUB_INDEX[_s[0]] = (_c, {
            "key": _s[0], "zh": _s[1], "brief": _s[2], "items": _s[3],
        })


def total_nodes() -> int:
    return len(CATEGORIES) + len(SUB_INDEX)


def resolve(key: str) -> tuple[str, str, str]:
    """Resolve a selection to (label_zh, en_brief, items_zh).

    Accepts a category key, a sub key, or 'random' (picks a random sub).
    """
    import random
    if not key or key == "random":
        cat = random.choice(CATEGORIES)
        sub = random.choice(cat["subs"])
        return f"{cat['zh']}·{sub[1]}", sub[2], sub[3]

    if key in SUB_INDEX:
        cat, sub = SUB_INDEX[key]
        return f"{cat['zh']}·{sub['zh']}", sub["brief"], sub["items"]

    for c in CATEGORIES:
        if c["key"] == key:
            # Whole-category pick: use the category brief, and the sub names as items
            names = "、".join(s[1] for s in c["subs"])
            return c["zh"], c["brief"], names

    # Unknown key: fall back to random rather than failing a draw
    cat = random.choice(CATEGORIES)
    sub = random.choice(cat["subs"])
    return f"{cat['zh']}·{sub[1]}", sub[2], sub[3]



def expand_to_subs(keys: list[str]) -> list[str]:
    """Expand a selection of categories and sub-classes into concrete sub keys.

    A category key contributes all of its sub-classes; a sub key contributes
    itself. The result is the pool a random draw may pick from.
    """
    out: list[str] = []
    seen: set[str] = set()
    for k in (keys or []):
        if not k:
            continue
        if k in SUB_INDEX:
            if k not in seen:
                seen.add(k)
                out.append(k)
            continue
        for c in CATEGORIES:
            if c["key"] == k:
                for sub in c["subs"]:
                    if sub[0] not in seen:
                        seen.add(sub[0])
                        out.append(sub[0])
                break
    return out


def pick_one_sub(keys: list[str]) -> str:
    """Randomly choose ONE concrete sub-class out of the selection.

    The model should be handed a single decided look, not a menu it has to
    choose from. Picking happens here so the prompt is deterministic once built.
    """
    import random
    pool = expand_to_subs(keys)
    if not pool:
        # Nothing valid selected: fall back to a random sub overall.
        cat = random.choice(CATEGORIES)
        return random.choice(cat["subs"])[0]
    return random.choice(pool)


def resolve_multi(keys: list[str]) -> tuple[str, str, str]:
    """Resolve a multi-selection to (label, brief, items) for ONE chosen sub-class.

    The selection is a RANGE, not a menu to hand to the model. A multi-pick means
    "any of these is fine", so one concrete sub-class is drawn here and only
    that one reaches the prompt — the model is never asked to choose, and never
    receives several looks at once.
    """
    keys = [k for k in (keys or []) if k]
    if not keys:
        return resolve("random")

    # Already a single, concrete choice: keep it as it is.
    if len(keys) == 1 and keys[0] in SUB_INDEX:
        return resolve(keys[0])

    picked = pick_one_sub(keys)
    label, brief, items = resolve(picked)
    return label, brief, items


def as_tree() -> list[dict]:
    """The shape the UI renders: categories with their sub-categories."""
    out = []
    for c in CATEGORIES:
        out.append({
            "key": c["key"],
            "zh": c["zh"],
            "en": c["en"],
            "brief": c["brief"],
            "subs": [
                {"key": s[0], "zh": s[1], "brief": s[2], "items": s[3]}
                for s in c["subs"]
            ],
        })
    return out
