#!/usr/bin/env python3
"""
Video Draft Creator - 主入口文件
支持 python -m video_draft_creator 执行
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main()) 