# -*- coding: utf-8 -*-
"""核心纯逻辑单元测试（标准库 unittest，不依赖浏览器 / CDP / 网络）。

跑：python tests/run_tests.py   或   python -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import api_writer, composer, moss_workflow


class TestSplitHeadshot(unittest.TestCase):
    def test_no_marker(self):
        comp, head = api_writer.split_headshot("a woman in a red dress")
        self.assertEqual(comp, "a woman in a red dress")
        self.assertEqual(head, "")

    def test_tail_marker(self):
        prompt = "a woman in red dress, 85mm-lens close-up -正面直视镜头，锁骨以上；[脸型]。-"
        comp, head = api_writer.split_headshot(prompt)
        self.assertIn("red dress", comp)
        self.assertNotIn("-正面", comp)          # 大头段必须从构图版里切走
        self.assertNotIn("85mm-lens", head)      # 正文里的连字符不能误当成标记
        self.assertTrue(head.startswith("-") and head.endswith("-"))

    def test_empty(self):
        self.assertEqual(api_writer.split_headshot(""), ("", ""))


class TestSavePrefix(unittest.TestCase):
    def test_view_and_composition(self):
        self.assertEqual(moss_workflow._save_prefix("", "front"), "正反面和大头/正面")
        self.assertEqual(moss_workflow._save_prefix("headshot", ""), "正反面和大头/大头")


class TestMatrixStats(unittest.TestCase):
    def test_total_positive(self):
        total = composer.matrix_stats()["total"]
        self.assertIsInstance(total, int)
        self.assertGreater(total, 0)


class TestRuleHotReload(unittest.TestCase):
    def test_load_rule_nonempty(self):
        rule = api_writer.load_head_prompt_rule()
        self.assertTrue(rule)
        self.assertIn("锁骨", rule)              # 规则核心约束仍在
        self.assertEqual(rule, api_writer.load_head_prompt_rule())  # 缓存命中


if __name__ == "__main__":
    unittest.main()
