#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit 工具可以将HTML文件翻译成双语版本，保留原始的HTML结构和样式。
主要特点:
1. 保留原始HTML样式和结构
2. 在每个段落后添加翻译内容
3. 支持多种翻译服务：谷歌翻译、微软翻译、Yandex翻译、Argos本地翻译
"""

import sys
from hfit.cli import main

if __name__ == "__main__":
    sys.exit(main()) 