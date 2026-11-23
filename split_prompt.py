"""split_prompt.py — 把 API 返回的提示词分离为构图版和大头版。

用法：
  py -3.13 split_prompt.py                      # 跑内置示例
  py -3.13 split_prompt.py 输入.txt             # 分离文件里的提示词
  py -3.13 split_prompt.py 输入.txt -o out_dir  # 并写出 构图版.txt / 大头版.txt

规则：模型按系统提示词的约定，把大头照片段用短横线包在整条提示词末尾（-XXX-）。
本脚本把该片段切出来：
  大头版 = -XXX-（保留前后短横线）
  构图版 = 去掉该片段后的其余部分
没有 -XXX- 时，构图版=原文，大头版=空。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.api_writer import split_headshot


def main(argv):
    if not argv:
        demo = ("photograph of a woman, oval face, espresso hair, red lips, "
                "black gown with thigh ring, standing full body, studio light "
                "- close-up headshot, camera at eye level, head upright, "
                "eyes on one horizontal line, shoulders square to frame, "
                "same oval face and espresso hair -")
        comp, head = split_headshot(demo)
        print("输入:\n", demo, "\n")
        print("构图版:\n", comp, "\n")
        print("大头版:\n", head)
        return 0

    src = argv[0]
    out_dir = None
    if "-o" in argv:
        i = argv.index("-o")
        out_dir = argv[i + 1] if i + 1 < len(argv) else None

    with open(src, encoding="utf-8") as f:
        text = f.read()
    comp, head = split_headshot(text)

    print("构图版 %d 字 | 大头版 %d 字" % (len(comp), len(head)))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "构图版.txt"), "w", encoding="utf-8") as f:
            f.write(comp)
        with open(os.path.join(out_dir, "大头版.txt"), "w", encoding="utf-8") as f:
            f.write(head)
        print("已写出:", os.path.join(out_dir, "构图版.txt"),
              os.path.join(out_dir, "大头版.txt"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
