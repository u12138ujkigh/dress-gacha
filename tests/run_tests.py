# -*- coding: utf-8 -*-
"""统一测试入口：跑核心单元测试。

用法：
    python tests/run_tests.py

历史遗留：tests/_verify_*.py 是早期依赖 CDP 端口的 E2E 脚本（需要 WebView2
远程调试端口），该端口已废弃，故这些脚本不再作为常规测试运行。回归测试以
本 runner 调用的 test_*.py 为准（纯 Python 逻辑，无需浏览器 / 网络）。
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        os.path.join(ROOT, "tests"), pattern="test_*.py", top_level_dir=ROOT)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
