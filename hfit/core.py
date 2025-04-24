#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Core translation logic for hfit.
"""

import time
from .translation_services import get_translation_service
from .html_processor import HTMLProcessor

def run_translation(input_file: str, 
                    output_file: str | None = None, 
                    source_language: str = 'en', 
                    target_language: str = 'zh-CN', 
                    translation_service_name: str = 'bing', 
                    mode: str = 'simple', 
                    html_debug: bool = False, 
                    trans_debug: bool = False):
    """执行核心的HTML文件翻译流程。

    Args:
        input_file: 输入HTML文件路径。
        output_file: 输出HTML文件路径 (可选)。
        source_language: 源语言代码。
        target_language: 目标语言代码。
        translation_service_name: 翻译服务名称。
        mode: 翻译模式 ('simple' 或 'advanced')。
        html_debug: 是否启用HTML处理调试信息。
        trans_debug: 是否启用翻译服务调试信息。
    
    Returns:
        str: 输出文件的路径。

    Raises:
        Exception: 如果翻译过程中出现任何错误。
    """
    preserve_tags_structure = (mode == 'advanced')

    print("\n========== hfit ==========")
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file or '自动生成'}")
    print(f"源语言：{source_language}")
    print(f"目标语言：{target_language}")
    print(f"翻译服务：{translation_service_name}")
    print(f"翻译模式：{'高级模式(保留语义块内的标签结构)' if preserve_tags_structure else '简单模式'}")
    print(f"HTML调试：{'开启' if html_debug else '关闭'}")
    print(f"翻译调试：{'开启' if trans_debug else '关闭'}")
    print("============================\n")

    start_time = time.time()

    try:
        print(f"[主程序] 正在初始化翻译服务：{translation_service_name}...")
        translation_service = get_translation_service(
            service_name=translation_service_name, 
            source_language=source_language, 
            target_language=target_language,
            debug=trans_debug
        )
        print(f"[主程序] 翻译服务初始化完成")
    except Exception as e:
        print(f"[错误] 初始化翻译服务失败: {str(e)}")
        raise  # 重新抛出异常以便上层处理

    print(f"[主程序] 正在初始化HTML处理器...")
    html_processor = HTMLProcessor(
        translation_service=translation_service,
        preserve_tags_structure=preserve_tags_structure,
        debug=html_debug
    )

    try:
        print(f"[主程序] 开始翻译文件...")
        final_output_file = html_processor.translate_file(input_file, output_file)
        elapsed_time = time.time() - start_time
        print(f"\n[主程序] 翻译完成！")
        print(f"[主程序] 输出文件：{final_output_file}")
        print(f"[主程序] 总耗时：{elapsed_time:.2f}秒")
        return final_output_file
    except Exception as e:
        print(f"[错误] 翻译过程中出现错误: {str(e)}")
        raise # 重新抛出异常以便上层处理 