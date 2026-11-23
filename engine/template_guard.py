# -*- coding: utf-8 -*-
"""Downgrade an external prompt template so it can live inside this project.

The templates live in the ComfyUI enhancer node's prompt_files folder, so they
cannot be edited in place — that would change the node's own behaviour. The
conflict has to be solved on the injection side instead.

A template is written for a DIFFERENT pipeline: it speaks English, it outputs
its own JSON schema (with a `ratio_follow` field this project does not have),
it decides the aspect ratio itself, and it treats the brief as a ceiling — the
eight-facet list is "optional", anything the brief did not mention is
forbidden. This project says the opposite on all four points: the output is
Chinese, the schema is rewritten_prompt / design_notes / wh_ratio, the ratio
comes from the tier, and every one of the seven design dimensions must be
filled in whether or not the brief mentioned it.

So the template is reduced to what is actually worth keeping — writing craft,
material knowledge, module libraries — and the parts that would set a rival
contract are removed:

    language    "always in English", "ready-to-paste English prompt"
    output      its own JSON schema, "output only the final prompt"
    ratio       "wh_ratio may only be …", "the ratio is decided by this contract"
    coverage    "the eight facets are an optional list", "brief is a ceiling"
    exposure    "the outfit is always rewritten as the exposed version"

Removal happens at three granularities, because that is what the templates are
made of:

    section   a heading whose whole section belongs to another contract
    block     a paragraph whose first line sets another contract
    line      a single sentence inside otherwise useful material

Whatever survives is followed by a notice that spells out which contract
wins, so the parts no rule could anticipate are still covered.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- the notice
# It goes AFTER the surviving template text: a rule that comes later in the
# system message is the one the model tends to follow.
OVERRIDE_NOTICE = (
    "【本项目覆盖声明】\n"
    "上面这段模板只提供写法与素材层面的补充。凡与系统提示词冲突之处，一律以系统提示词为准：\n"
    "- 输出语言固定中文（见系统提示词「输出语言」）。\n"
    "- 输出格式固定为单个 JSON 对象，字段为 rewritten_prompt / design_notes / wh_ratio"
    "（见所选档位的输出要求）。\n"
    "- 画面比例由所选档位的输出要求统一决定，模板内的比例取值与判定规则作废。\n"
    "- 维度覆盖范围按系统提示词「设计维度与顺序」逐项给全，"
    "模板内「只写 brief 提到的」「可选清单」「不许补」这类取舍规则作废。\n"
    "- 服装暴露程度按所选档位与「服装详细度」执行，模板内的服装改写规则作废。\n"
    "- 提示词正文写成单段连续中文，不换行。"
)

# ---------------------------------------------------------------- headings
# A heading is either markdown or a bare title line. The moodyMOSS template
# uses bare uppercase titles ("CAPTION OUTPUT"), the Chinese ones use
# markdown. Both have to be recognised or half the contracts survive.
#
# The bare-title test has to be strict. The templates are full of table rows
# ("输入\t模式\t首要动作") and of hard-wrapped English paragraphs; treating
# either as a heading would cut every section boundary in the wrong place.
# A bare title is short, has no sentence punctuation, no tab, no quote and
# no clause-internal comma.
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BARE_IGNORED = {"代码块"}


def _is_bare_heading(line: str) -> bool:
    """A title line: short, no sentence punctuation, not a list item."""
    s = line.strip()
    if not s or len(s) > 60:
        return False
    if s[0] in "-*#>|`:":
        return False
    if "\t" in s:
        return False
    if "'" in s or '"' in s:
        return False
    if any(ch in s for ch in ",，;；、。"):
        return False
    # A sentence ends with punctuation; a title does not.
    if s[-1] in ".,;:!?、。，；：！？":
        return False
    if not s[0].isalpha():
        return False
    if s in _BARE_IGNORED:
        return False
    return True


def _heading_of(line: str) -> tuple[int, str] | None:
    """Return (level, title) if the line is a heading.

    A bare title is the top level: it owns everything until the next title of
    any kind. That is how the moodyMOSS template is organised, and it keeps
    the section spans correct when bare titles sit inside markdown sections.
    """
    m = _MD_HEADING.match(line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    if _is_bare_heading(line):
        return 1, line.strip()
    return None


def _walk_headings(lines):
    """Yield (index, level, title) for every heading in the text."""
    if isinstance(lines, str):
        lines = lines.split("\n")
    for i, line in enumerate(lines):
        h = _heading_of(line)
        if h:
            yield i, h[0], h[1]


def _section_spans(lines) -> list[tuple[int, int, int, str]]:
    """Return (start, end, level, title) for every section.

    A section runs from its heading to the next heading of the same or a
    shallower level. That end index is what makes a section removable as a
    whole — dropping only the heading line would leave the contract behind.
    """
    hs = list(_walk_headings(lines))
    spans: list[tuple[int, int, int, str]] = []
    for k, (i, lvl, title) in enumerate(hs):
        end = len(lines)
        for j, l2, _t in hs[k + 1:]:
            if l2 <= lvl:
                end = j
                break
        spans.append((i, end, lvl, title))
    return spans


# ---------------------------------------------------------------- the rules
# Section level: the whole section belongs to another contract.
_SECTION_DROP = (
    re.compile(r"输出格式"),
    re.compile(r"Output\s*[Ff]ormat"),
    re.compile(r"^Language$", re.I),
    re.compile(r"Output\s+Size\s+Determination", re.I),
    re.compile(r"FINAL\s+RESPONSE\s+CONTRACT", re.I),
    re.compile(r"CAPTION\s+OUTPUT", re.I),
    re.compile(r"CAPTION\s+ARCHITECTURE", re.I),
    re.compile(r"OUTPUT\s+MODE\s+SELECTION", re.I),
    re.compile(r"MOSS\s+LAYOUT", re.I),
    re.compile(r"露骨度五档"),
    re.compile(r"长度按\s*brief"),
    re.compile(r"组装流程"),
    re.compile(r"^示例[一二三四五六七八九十]"),
    # The outfit rewrite contract: every mentioned garment is turned into its
    # exposed version. This project decides exposure by tier and by the
    # detail module, so the whole mapping goes.
    re.compile(r"服装状态映射"),
)

# Section level, rewritten: the section stays, its premise changes.
_SECTION_REWRITE = (
    # The template declaring itself above everything else in the message.
    (re.compile(r"^最高准则（高于本文其余全部内容）"), "最高准则"),
    # The coverage contract: the eight facets are an assignment, not a menu.
    (re.compile(r"^覆盖面按\s*brief\s*决定，不是作业清单"),
     "八面清单（逐项给全，不按 brief 增删）"),
)

# Block level: the first line of a paragraph owns the contract.
_BLOCK_DROP = (
    re.compile(r"^#{1,6}\s*输出格式"),
    re.compile(r"^输出格式"),
    re.compile(r"^#{1,6}\s*Output\s*[Ff]ormat", re.I),
    re.compile(r"^#{1,6}\s*Language\s*$", re.I),
    re.compile(r"^#{1,6}\s*FINAL RESPONSE CONTRACT", re.I),
    re.compile(r"^#{1,6}\s*CAPTION OUTPUT", re.I),
    re.compile(r"^#{1,6}\s*OUTPUT MODE SELECTION", re.I),
    re.compile(r"^#{1,6}\s*MOSS LAYOUT", re.I),
    re.compile(r"^#{1,6}\s*露骨度五档"),
    re.compile(r"^#{1,6}\s*长度按\s*brief"),
    re.compile(r"^#{1,6}\s*组装流程"),
    re.compile(r"^\*\*FIRST — there are TWO separate language decisions", re.I),
    re.compile(r"^\*\*\(A\) Language of", re.I),
    re.compile(r"^\*\*\(B\) Language of", re.I),
    re.compile(r"^Worked example: image is mostly", re.I),
    re.compile(r"^Two reinforcements on decision \(B\)", re.I),
    re.compile(r"^CAPTION ARCHITECTURE"),
    re.compile(r"^比例判定"),
    re.compile(r"^比例[。：]"),
    re.compile(r"^细节只准补两类"),
    re.compile(r"^保真第一"),
    re.compile(r"^- brief (只有|有|提到)"),
    re.compile(r"^格式约定"),
)

# Line level: single sentences that set a rival contract.
_LINE_DROP = (
    # The template declaring itself above everything else in the message.
    re.compile(r"本文其余全部条款与本段冲突时，一律以本段为准"),
    # The template's own output mode.
    re.compile(r"^4\.\s*Use the correct MOSS prompt output format", re.I),
    re.compile(r"^5\.\s*Output ONLY the final positive prompt", re.I),
    # The template's own JSON field list and its ratio whitelist.
    re.compile(r"^rewritten_prompt\s*禁含分辨率信息"),
    re.compile(r"^rewritten_prompt 必填非空"),
    re.compile(r"^\s*\{\"rewritten_prompt\""),
    # Coverage: the brief as a ceiling, the facets as an optional list.
    re.compile(r"^操作顺序：先把 brief 里的名词与动词全部抄出来"),
    re.compile(r"^操作判据：把 caption 里每一处人物"),
    re.compile(r"^升档降档。用户说"),
    re.compile(r"^解。其余缺少非关键细节时直接作合理创作决定"),
    re.compile(r"^文字与逐图输出是否满足要求"),
    re.compile(r"^篇幅是否落在对应档位内"),
    # Batch / code-block output: a different output shape.
    re.compile(r"^多图用“第 \d+ 张｜"),
    re.compile(r"^每张图独立成稿："),
)

# Phrase level: a clause inside a longer sentence that has to go.
_PHRASE_DROP = (
    (re.compile(r"仍给含蓄版则检查是否被档位规则覆盖，把器官和动词换回直白词。"), ""),
    (re.compile(r"衣物只写暴露版则回到服装映射逐件落状态。"), ""),
    (re.compile(r"用户指定强度则照办，未指定按素材推断，默认落在直白档。"),
     "强度按所选档位执行。"),
    # The moodyMOSS Chinese content note ends with an output-format clause.
    (re.compile(r"输出只包含提示词本身，不要任何解释、前言或后缀。"),
     "输出按系统提示词规定的 JSON 字段给出，不要任何解释、前言或后缀。"),
    # "不编造 X" phrasings read as a coverage ceiling ("don't add what the
    # brief did not name"); the meaning is kept, the framing is moved onto
    # the project's own dimension rule.
    (re.compile(r"不编造剧情对白与身世"),
     "剧情对白与身世不作额外虚构；人物、服装等维度仍按系统提示词逐项给全"),
    (re.compile(r"不编造转录"), "不作凭空转录"),
)

# Line level, rewritten instead of removed: the sentence still carries useful
# material, only the contract part has to go.
_LINE_REWRITE = (
    # "优先使用英文直白词" → Chinese output, the word list stays as reference.
    (re.compile(r"优先使用英文直白词"),
     "用中文写出具体的器官与动作词（后面的英文词表只是对照）："),
    (re.compile(r"身体反应库\(按需取用，至少落两项\)"),
     "身体反应库(按需取用，至少落两项，用中文写)"),
    (re.compile(r"质感硬性。每一处裸露都要写皮肤在当前光线下的状态"),
     "质感硬性。每一处裸露都要用中文写皮肤在当前光线下的状态"),
    (re.compile(r"ready-to-paste English positive image-generation prompt", re.I),
     "ready-to-paste 中文正向图像生成提示词"),
    (re.compile(r"one long English paragraph", re.I),
     "one long Chinese paragraph"),
    (re.compile(r"The description is always in English", re.I),
     "The description is always in Chinese"),
    (re.compile(r"完整英文场景描述"), "完整中文场景描述"),
    # The avatar template's own exposure rewrite.
    (re.compile(r"服装是永远的被改目标"),
     "服装按系统提示词的档位与维度执行"),
    (re.compile(r"服装规则\(硬性\)。输入人物服装一律改为暴露版无例外，用户不提也视为默认。"),
     "服装状态映射（只在所选档位允许的暴露范围内使用）："),
    (re.compile(r"确定比例。"), ""),
    (re.compile(r"JSON外无文字。"), ""),
    # The WorkfMOSS template's output wording.
    (re.compile(r"只给最终提示词"), "只输出 JSON"),
    (re.compile(r"默认只给一个 text 代码块，内容是完整中文自然语言提示词"),
     "默认只给一个 JSON 对象，内容是完整中文提示词"),
    # The WorkfMOSS reference-image rule: the useful half stays, the half that
    # tells the model not to fill the dimensions goes.
    (re.compile(r"禁止把推测与不明写成确定事实；禁止为补全而新增人物、道具、光源或事件。"),
     "禁止把推测与不明写成确定事实；人物、道具、光源与事件按系统提示词"
     "「设计维度与顺序」逐项给全。"),
    (re.compile(r"可选项（次要装饰，只在增加视觉信息时写入）"),
     "次要装饰（在增加视觉信息时写入）"),
    # The moodyMOSS template's three-bucket split: "optional" is a coverage
    # rule this project does not share.
    (re.compile(r";\s*omit OPTIONAL details unless they add visual value", re.I),
     ""),
    (re.compile(r"and OPTIONAL \(secondary decoration\)"),
     "and secondary decoration (装饰项，不影响维度覆盖)"),
    # The MOSS self-check: the length bucket belongs to another contract.
    (re.compile(r"没有场景级发明"), "没有与设计维度无关的凭空添加"),
    # The MOSS self-check and the length note both ask for "no invented
    # scene-level content"; this project asks for every dimension to be there.
    (re.compile(r"caption 里每个人物/物体/动作在 brief 里都有依据"),
     "每个设计维度都写到了"),
    (re.compile(r"多写的每一个词都必须是渲染级细节，不能是场景级发明"),
     "每个设计维度都要写到，多写的部分也要服务于维度本身"),
    # The MOSS coverage section: eight facets are an assignment, not a menu.
    (re.compile(r"八面只是\*\*可选清单\*\*，不是必须写完的任务。"
                r"brief 提到哪面就写哪面，没提的跳过，\*\*绝不许为了凑面而编\*\*。"),
     "八面每一面都要写全，brief 没提到的面同样要写。"),
)


def _drop_sections(lines) -> set[int]:
    """Line indices of every section that belongs to another contract."""
    spans = _section_spans(lines)
    drop: set[int] = set()
    for (i, end, _lvl, title) in spans:
        if any(p.search(title) for p in _SECTION_DROP):
            drop.update(range(i, end))
    return drop


def _rewrite_sections(lines, drop: set[int]):
    """Rewrite the title of a section whose premise changed."""
    out = list(lines)
    for (i, _end, _lvl, title) in _section_spans(lines):
        if i in drop:
            continue
        for pat, repl in _SECTION_REWRITE:
            if pat.search(title):
                new = pat.sub(repl, title)
                line = lines[i]
                m = _MD_HEADING.match(line)
                if m:
                    raw = m.group(2)
                    trail = raw[len(raw.strip()):]
                    out[i] = m.group(1) + " " + new + trail
                else:
                    out[i] = new
                break
    return out


def _drop_blocks(text: str) -> tuple[str, int]:
    """Remove a whole paragraph when its first line owns a rival contract."""
    blocks = re.split(r"\n\s*\n", text)
    kept: list[str] = []
    dropped = 0
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        first = stripped.split("\n")[0].strip()
        if any(p.search(first) for p in _BLOCK_DROP):
            dropped += 1
            continue
        kept.append(stripped)
    return "\n\n".join(kept), dropped


def _clean_lines(text: str) -> tuple[str, int]:
    """Drop or rewrite the individual sentences that set a rival contract."""
    out: list[str] = []
    dropped = 0
    for line in text.split("\n"):
        stripped = line.strip()
        if any(p.search(stripped) for p in _LINE_DROP):
            dropped += 1
            continue
        for pat, repl in _PHRASE_DROP:
            line = pat.sub(repl, line)
        for pat, repl in _LINE_REWRITE:
            line = pat.sub(repl, line)
        out.append(line)
    return "\n".join(out), dropped


def sanitize_template(text: str) -> tuple[str, dict]:
    """Downgrade an external template and report what was removed.

    Returns (cleaned_text, stats). The stats count dropped lines and blocks so
    the caller can show the user that something actually happened.
    """
    raw = text or ""
    stats = {"chars_in": len(raw), "chars_out": 0, "lines_dropped": 0,
             "blocks_dropped": 0, "sections_dropped": 0}

    def _count_lines(s: str) -> int:
        return len([x for x in s.split("\n") if x.strip()])

    lines = raw.split("\n")
    drop = _drop_sections(lines)
    stats["sections_dropped"] = sum(
        1 for (i, end, _lvl, title) in _section_spans(lines)
        if i in drop
    )

    lines = _rewrite_sections(lines, drop)
    lines = [l for i, l in enumerate(lines) if i not in drop]
    work = "\n".join(lines)

    work, dropped = _drop_blocks(work)
    stats["blocks_dropped"] += dropped

    before = _count_lines(work)
    work, dropped = _clean_lines(work)
    stats["lines_dropped"] += dropped

    work = re.sub(r"\n{3,}", "\n\n", work).strip()
    stats["chars_out"] = len(work)
    return work, stats


def compose_template_block(text: str) -> tuple[str, dict]:
    """Build the system block for a template: cleaned text plus the notice."""
    cleaned, stats = sanitize_template(text)
    if not cleaned.strip():
        return "", stats
    body = (
        "## 附加约束（来自所选提示词模板）\n\n"
        + cleaned.strip()
        + "\n\n"
        + OVERRIDE_NOTICE
    )
    stats["chars_out"] = len(body)
    return body, stats
