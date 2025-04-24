#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit CLI Entry Point

Handles command-line argument parsing and initiates the translation process.
"""

import sys
import argparse
# 从 .core 导入核心翻译函数
from .core import run_translation 
# 从 .config 导入命令行选项所需的常量
from .config import TRANSLATION_SERVICE_OPTIONS

# 翻译工具命令行选项
def add_translation_options(parser):
    """添加hfit的通用命令行选项
    
    Args:
        parser: argparse.ArgumentParser 实例
    """
    parser.add_argument("-i", "--input-file", dest="input_file", help="要翻译的HTML文件")
    parser.add_argument("-o", "--output-file", dest="output_file", help="输出的HTML文件路径")
    parser.add_argument("-s", "--service", dest="translation_service", 
                        choices=TRANSLATION_SERVICE_OPTIONS, default="bing",
                        help=f"翻译服务类型，支持: {', '.join(TRANSLATION_SERVICE_OPTIONS)}")
    
    parser.add_argument("--from", dest="source_language", default="en", 
                        help="源语言代码，默认: en (英语)")
    parser.add_argument("--to", dest="target_language", default="zh-CN", 
                        help="目标语言代码，默认: zh-CN (简体中文)")
    
    # 翻译模式选项
    parser.add_argument("-mode", choices=['simple', 'advanced'], default='simple',
                        help="翻译模式：simple(简单模式，不保留标签结构)或advanced(高级模式，保留语义块内的标签结构)")
    
    # 调试选项
    parser.add_argument("-debug", "--verbose", dest="debug", action="store_true", default=False,
                        help="显示调试信息")
    parser.add_argument("-html-debug", dest="html_debug", action="store_true", default=False,
                        help="仅显示HTML处理的调试信息")
    parser.add_argument("-trans-debug", dest="trans_debug", action="store_true", default=False,
                        help="仅显示翻译服务的详细调试信息")

def main():
    """命令行入口函数
    
    解析命令行参数并启动翻译流程
    """
    parser = argparse.ArgumentParser(description="hfit - HTML双语翻译工具")
    # 位置参数应在选项之前添加，或者根据你的偏好调整
    # parser.add_argument("input_file_pos", metavar="input_file", nargs="?", help="要翻译的HTML文件 (位置参数)")
    add_translation_options(parser)
    args = parser.parse_args()

    # 如果使用位置参数，需要处理它与 -i/--input-file 的关系
    # input_file = args.input_file_pos or args.input_file
    # if not input_file:
    #     parser.print_help()
    #     sys.exit(1)
    # 简化：当前只使用 -i/--input-file 或 --input_file 参数
    if not args.input_file:
         parser.print_help()
         print("\n错误：缺少输入文件。请使用 -i 或 --input-file 指定。")
         sys.exit(1)

    html_debug = args.html_debug or args.debug
    trans_debug = args.trans_debug or args.debug

    try:
        run_translation(
            input_file=args.input_file,
            output_file=args.output_file,
            source_language=args.source_language,
            target_language=args.target_language,
            translation_service_name=args.translation_service,
            mode=args.mode,
            html_debug=html_debug,
            trans_debug=trans_debug
        )
        return 0 # 成功退出
    except Exception:
        # 错误信息已在 run_translation 中打印
        return 1 # 失败退出

if __name__ == "__main__":
    sys.exit(main()) 