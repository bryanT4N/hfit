#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit 配置模块

这个模块包含了项目的配置信息和常量:
1. 文本处理标记
2. HTML 标签分类
3. 支持的翻译服务列表
4. 默认CSS样式
5. UUID 生成函数
"""

import uuid

# 标记标识符
START_MARK = "@%"
END_MARK = "#$"
START_MARK0 = "@ %"
END_MARK0 = "# $"

# 不翻译的HTML标签
HTML_TAGS_NO_TRANSLATE = ['TITLE', 'SCRIPT', 'STYLE', 'TEXTAREA', 'SVG', 'svg']
HTML_TAGS_INLINE_IGNORE = ['BR', 'CODE', 'KBD', 'WBR']
HTML_TAGS_INLINE_TEXT = ['A', 'ABBR', 'ACRONYM', 'B', 'BDO', 'BIG', 'CITE', 'DFN', 'EM', 'I', 'LABEL', 'Q', 'S', 'SMALL', 'SPAN', 'STRONG', 'SUB', 'SUP', 'U', 'TT', 'VAR']

TRANSLATION_SERVICE_OPTIONS = [
    "google",
    "bing", 
    "yandex",
    "argos"
]

# 样式CSS - 与原项目风格一致但更改标识符
DEFAULT_CSS = '''
:root {
  --hfit-theme-underline-borderColor: #72ece9;
  --hfit-theme-nativeUnderline-borderColor: #72ece9;
  --hfit-theme-nativeDashed-borderColor: #72ece9;
  --hfit-theme-nativeDotted-borderColor: #72ece9;
  --hfit-theme-highlight-backgroundColor: #ffff00;
  --hfit-theme-dashed-borderColor: #59c1bd;
  --hfit-theme-blockquote-borderColor: #cc3355;
  --hfit-theme-thinDashed-borderColor: #ff374f;
  --hfit-theme-dashedBorder-borderColor: #94a3b8;
  --hfit-theme-dashedBorder-borderRadius: 0;
  --hfit-theme-solidBorder-borderColor: #94a3b8;
  --hfit-theme-solidBorder-borderRadius: 0;
  --hfit-theme-dotted-borderColor: #94a3b8;
  --hfit-theme-wavy-borderColor: #72ece9;
  --hfit-theme-dividingLine-borderColor: #94a3b8;
  --hfit-theme-grey-textColor: #2f4f4f;
  --hfit-theme-marker-backgroundColor: #fbda41;
  --hfit-theme-marker-backgroundColor-rgb: 251, 218, 65;
  --hfit-theme-marker2-backgroundColor: #ffff00;
  --hfit-theme-background-backgroundColor: #dbafaf;
  --hfit-theme-background-backgroundColor-rgb: 219, 175, 175;
  --hfit-theme-background-backgroundOpacity: 12;
  --hfit-theme-opacity-opacity: 10;
}

[hfit-state="dual"] .hfit-target-translation-pre-whitespace {
  white-space: pre-wrap !important;
}

[hfit-state="dual"] .hfit-target-wrapper[dir="rtl"] {
  text-align: right;
}

[hfit-state="translation"] .hfit-target-wrapper > br {
  display: none;
}

[hfit-state="translation"]
  .hfit-target-translation-block-wrapper {
  margin: 0 !important;
}

[hfit-state="dual"] .hfit-target-translation-block-wrapper {
  margin: 8px 0 !important;
  display: inline-block;
}

[hfit-trans-position="before"]
  .hfit-target-translation-block-wrapper {
  display: block;
}

[hfit-trans-position="before"]
  .hfit-target-translation-block-wrapper {
  margin-top: 0 !important;
}

.hfit-target-wrapper {
  word-break:break-word; 
  user-select:text;
}

[dir='rtl'] .hfit-target-wrapper:not([dir]) {
  text-align:left;
}

[hfit-state=dual] .hfit-target-translation-block-wrapper-theme-dividingLine::before {
  display:block;
}

[hfit-trans-position=before] .hfit-target-translation-block-wrapper {
  display:block!important;
}
'''

DYNAMIC_CSS = '''.hfit-target-wrapper[dir='rtl'] {text-align: right;}
.hfit-target-wrapper[dir='rtl'] [data-hfit-class-bak*='block-wrapper'] {display:block;}
.hfit-target-wrapper {word-break:break-word; user-select:text;}
[hfit-state="translation"] .hfit-target-wrapper[dir='rtl'] {display:inline-block;}
[dir='rtl'] .hfit-target-wrapper:not([dir]) {text-align:left;}
[hfit-state=dual] .hfit-target-translation-block-wrapper-theme-dividingLine::before {display:block;}
[hfit-trans-position=before] .hfit-target-translation-block-wrapper {display:block!important;}'''

USER_CUSTOM_CSS = ''':root {

.hfit-target-inner { font-family: inherit; }


.hfit-target-inner { font-family: inherit; }
}'''

def generate_session_id():
    """生成唯一的会话ID
    
    Returns:
        str: UUID字符串
    """
    return str(uuid.uuid4()) 