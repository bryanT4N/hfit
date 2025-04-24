#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit 的HTML处理模块

这个模块负责HTML的解析和双语显示:
1. 找到需要翻译的段落
2. 处理HTML结构并保留样式
3. 将翻译后的内容插入到HTML中
"""

import os
import copy
import time
from bs4 import BeautifulSoup, NavigableString, Comment, Tag
from typing import List, Dict, Optional

from hfit.config import HTML_TAGS_NO_TRANSLATE, HTML_TAGS_INLINE_TEXT, HTML_TAGS_INLINE_IGNORE, DEFAULT_CSS, DYNAMIC_CSS, USER_CUSTOM_CSS, generate_session_id
from hfit.translation_services import TranslationService

class HTMLProcessor:
    """HTML处理器，负责处理HTML的解析和双语显示
    
    这个类负责:
    1. 解析HTML文档
    2. 找到需要翻译的段落
    3. 调用翻译服务翻译内容
    4. 将翻译结果添加到原始HTML中
    """
    
    def __init__(self, translation_service: TranslationService, preserve_tags_structure=True, debug=True):
        """初始化HTML处理器
        
        Args:
            translation_service: 翻译服务实例
            preserve_tags_structure: 是否保留语义块内的标签结构
            debug: 是否显示调试信息
        """
        self.translation_service = translation_service
        self.session_id = generate_session_id()
        self.preserve_tags_structure = preserve_tags_structure
        self.debug = debug
        self.elements_count = 0
        self.processed_count = 0
        
    def debug_print(self, message):
        """输出调试信息
        
        Args:
            message: 要输出的信息
        """
        if self.debug:
            print(message, flush=True)
            
    def translate_file(self, input_file: str, output_file: Optional[str] = None) -> str:
        """翻译HTML文件并保存结果
        
        Args:
            input_file: 输入HTML文件路径
            output_file: 输出HTML文件路径，如果不指定则自动生成
            
        Returns:
            输出文件的路径
        
        Raises:
            FileNotFoundError: 如果输入文件不存在
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"无法找到输入文件：{input_file}")
            
        # 如果未指定输出文件，创建默认名称
        if not output_file:
            basename = os.path.basename(input_file)
            dirname = os.path.dirname(input_file)
            name, ext = os.path.splitext(basename)
            output_file = os.path.join(dirname, f"{name}_translated{ext}")
        
        self.debug_print(f"\n[HTML处理] 开始处理文件: {input_file}")
        self.debug_print(f"[HTML处理] 输出文件: {output_file}")
        self.debug_print(f"[HTML处理] 翻译模式: {'保留语义块内的标签结构' if self.preserve_tags_structure else '简单模式'}")
            
        # 读取HTML文件
        self.debug_print(f"[HTML处理] 正在读取文件...")
        start_time = time.time()
        
        with open(input_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        file_size = len(html_content)
        read_time = time.time() - start_time
        self.debug_print(f"[HTML处理] 文件读取完成，大小: {file_size} 字节，耗时: {read_time:.2f}秒")
            
        # 翻译HTML内容
        self.debug_print(f"[HTML处理] 开始翻译HTML内容...")
        translate_start_time = time.time()
        translated_html = self.translate_html_content(html_content)
        translate_time = time.time() - translate_start_time
        self.debug_print(f"[HTML处理] 翻译完成，处理了 {self.processed_count} 个段落，耗时: {translate_time:.2f}秒")
        
        # 保存翻译后的文件
        self.debug_print(f"[HTML处理] 正在保存输出文件...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_html)
            
        total_time = time.time() - start_time
        self.debug_print(f"[HTML处理] 处理完成，总耗时: {total_time:.2f}秒")
            
        return output_file
    
    def _add_styles(self, soup):
        """添加必要的CSS样式到HTML头部
        
        添加三种样式:
        1. 默认CSS - 基本样式定义
        2. 动态CSS - 动态生成的样式
        3. 用户自定义CSS - 用户可以自定义的样式
        
        Args:
            soup: BeautifulSoup解析的HTML文档
        """
        head = soup.find('head')
        if not head:
            head = soup.new_tag('head')
            soup.html.insert(0, head)
        
        # 添加默认CSS样式
        style_tag = soup.new_tag('style')
        style_tag['data-id'] = 'hfit-default-injected-css'
        style_tag.string = DEFAULT_CSS
        head.append(style_tag)
        
        # 添加动态CSS
        dynamic_style = soup.new_tag('style')
        dynamic_style['data-id'] = 'hfit-dynamic-injected-css'
        dynamic_style.string = DYNAMIC_CSS
        head.append(dynamic_style)
        
        # 添加用户自定义样式
        user_style = soup.new_tag('style')
        user_style['data-id'] = 'hfit-user-custom-style'
        user_style.string = USER_CUSTOM_CSS
        head.append(user_style)
    
    def _find_paragraphs(self, soup):
        """查找文档中所有需要翻译的段落
        
        使用递归遍历来查找所有的文本段落，包括嵌套在多层标签中的文本。
        构建段落规则：
        1. 遇到非内联元素时，将该元素标记为新段落
        2. 遇到<br>标签后的下一个元素，无论是否为内联元素，都标记为新段落
        3. 访问非内联元素整个块结束，视为紧接着存在一个换行符<br>
        4. 当<br>标签后面直接跟随文本（非元素）时，将该文本包装到span标签并标记为段落
        
        Args:
            soup: BeautifulSoup解析的HTML文档
            
        Returns:
            需要翻译的HTML元素列表
        """
        # 存储需要翻译的段落元素
        paragraphs_to_translate = []
        
        # 记录已经被标记为段落的元素，避免重复
        marked_elements = set()
        
        # 记录是否刚刚遇到了<br>标签或非内联块结束
        just_saw_br = [False]  # 使用列表以便在递归中修改
        
        def mark_as_paragraph(element):
            """将元素标记为段落，并添加到需要翻译的列表中
            
            Args:
                element: 要标记的HTML元素
            """
            if element not in marked_elements and isinstance(element, Tag):
                # 标记元素
                if not element.has_attr('data-hfit-paragraph'):
                    element['data-hfit-paragraph'] = '1'
                
                if not element.has_attr('data-hfit-walked'):
                    element['data-hfit-walked'] = self.session_id
                
                # 添加到段落列表
                if element not in paragraphs_to_translate:
                    paragraphs_to_translate.append(element)
                    marked_elements.add(element)
        
        def process_element(element, parent=None):
            """递归处理元素及其子元素
            
            Args:
                element: 当前处理的元素
                parent: 父元素
            """
            # 检查是否应该跳过该元素
            if (isinstance(element, Tag) and (
                element.name.upper() in HTML_TAGS_NO_TRANSLATE or
                element.get('class') and 'notranslate' in element.get('class') or
                element.get('translate') == 'no')):
                return
            
            # 如果是br标签，标记下一个元素，并处理后面的文本节点
            if isinstance(element, Tag) and element.name.upper() == 'BR':
                just_saw_br[0] = True
                
                # 处理br后面直接跟随的文本节点
                if parent and element.next_sibling and isinstance(element.next_sibling, NavigableString):
                    # 收集从br后到下一个br或父元素结束的所有连续文本
                    text_nodes = []
                    current = element.next_sibling
                    
                    # 收集所有连续的文本节点，直到遇到br标签或非文本节点
                    while current and isinstance(current, NavigableString):
                        if current.strip():  # 只处理非空文本
                            text_nodes.append(current)
                        # 移动到下一个兄弟节点
                        next_node = current.next_sibling
                        # 如果下一个节点是br，则停止收集
                        if next_node and isinstance(next_node, Tag) and next_node.name.upper() == 'BR':
                            break
                        current = next_node
                    
                    # 如果收集到了文本节点，创建span包装它们
                    if text_nodes:
                        # 取第一个文本节点作为位置标记
                        first_text = text_nodes[0]
                        # 创建一个新的span元素
                        span = soup.new_tag('span')
                        span['data-hfit-generated'] = '1'  # 标记这是自动生成的元素
                        
                        # 将所有文本节点内容合并
                        combined_text = ''.join(str(node) for node in text_nodes)
                        span.string = combined_text
                        
                        # 用新的span替换第一个文本节点
                        first_text.replace_with(span)
                        
                        # 删除剩余的文本节点
                        for node in text_nodes[1:]:
                            if node.parent:  # 确保节点还在DOM树中
                                node.extract()
                        
                        # 标记这个span为段落
                        mark_as_paragraph(span)
                
                return
            
            # 检查元素是否为非内联元素
            is_non_inline = False
            if isinstance(element, Tag):
                is_non_inline = element.name.upper() not in HTML_TAGS_INLINE_TEXT and element.name.upper() not in HTML_TAGS_INLINE_IGNORE
            
            # 这两种情况需要将元素标记为新段落：
            # 1. 如果是非内联元素
            # 2. 如果刚刚看到了<br>标签或非内联块结束
            if isinstance(element, Tag):
                if is_non_inline or just_saw_br[0]:
                    mark_as_paragraph(element)
                    just_saw_br[0] = False  # 重置标记
            
            # 处理子元素
            if isinstance(element, Tag):
                previous_br_state = just_saw_br[0]  # 保存当前br状态
                
                # 首先处理直接子元素
                for child in element.children:
                    process_element(child, element)
                
                # 规则3：非内联元素块结束后，设置just_saw_br为True
                if is_non_inline:
                    just_saw_br[0] = True
                else:
                    # 恢复处理完子元素后的br状态
                    just_saw_br[0] = previous_br_state
        
        # 开始处理
        if soup.body:
            process_element(soup.body)
        else:
            process_element(soup)
        
        # 第二次遍历：找出带有文本内容但尚未标记为段落的元素
        def find_text_elements(element, parent=None):
            """找出包含文本的元素
            
            Args:
                element: 当前处理的元素
                parent: 父元素
            """
            if isinstance(element, NavigableString) and not isinstance(element, Comment) and element.strip():
                # 找到文本节点的容器元素
                container = element.parent
                while (container and isinstance(container, Tag) and 
                       container.name.upper() in HTML_TAGS_INLINE_TEXT and 
                       container not in marked_elements):
                    container = container.parent
                
                if container and isinstance(container, Tag) and container not in marked_elements:
                    mark_as_paragraph(container)
            
            # 递归处理子元素
            if isinstance(element, Tag) and element.name.upper() not in HTML_TAGS_NO_TRANSLATE:
                for child in element.children:
                    find_text_elements(child, element)
        
        # 查找包含文本的元素
        if soup.body:
            find_text_elements(soup.body)
        else:
            find_text_elements(soup)
        
        # 调试输出
        self.debug_print(f"[HTML处理] 找到 {len(paragraphs_to_translate)} 个需要翻译的段落")
        
        return paragraphs_to_translate
    
    def _create_translation_wrapper(self, translated_text, is_simple_mode=False):
        """创建翻译包装器
        
        创建包含翻译结果的HTML包装器。
        
        Args:
            translated_text: 翻译后的文本内容
            is_simple_mode: 是否是简单模式，如果是则设置深灰色样式
            
        Returns:
            BeautifulSoup对象，表示包装后的翻译内容
        """
        # 创建翻译包装器
        # 如果是简单模式，添加深灰色样式
        inner_style = ' style="color:#2f4f4f;"' if is_simple_mode else ''
        
        wrapper_html = (
            f'<font class="notranslate hfit-target-wrapper" '
            f'data-hfit-translation-element-mark="1" lang="{self.translation_service.target_language}">'
            f'<br>'
            f'<font class="notranslate hfit-target-translation-theme-none '
            f'hfit-target-translation-block-wrapper-theme-none '
            f'hfit-target-translation-block-wrapper" '
            f'data-hfit-translation-element-mark="1">'
            f'<font class="notranslate hfit-target-inner '
            f'hfit-target-translation-theme-none-inner" '
            f'data-hfit-translation-element-mark="1"{inner_style}>'
            f'{translated_text}'
            f'</font></font></font>'
        )
        
        # 解析翻译包装器
        wrapper = BeautifulSoup(wrapper_html, 'html.parser').find('font')
        
        return wrapper
    
    def _translate_semantic_block_with_structure(self, element):
        """翻译语义块并保留其HTML结构
        
        这种方法直接深度复制元素的DOM结构，
        然后处理每个文本节点，保留所有标签和属性。
        
        Args:
            element: 要翻译的HTML元素/语义块
        """
        # 标记段落已处理
        element['data-hfit-paragraph'] = '1'
        
        # 处理前检查元素是否已包含翻译
        if element.find(attrs={"data-hfit-translation-element-mark": "1"}):
            # 清除所有已存在的翻译标记，避免重复翻译
            for node in element.find_all(attrs={"data-hfit-translation-element-mark": "1"}):
                node.decompose()
        
        # 直接处理整个元素，不再检查<br>标签
        self._process_single_block(element)
    
    def _process_single_block(self, element):
        """处理单个内容块的翻译
        
        Args:
            element: 要处理的HTML元素
        """
        # 深度复制元素
        element_clone = copy.deepcopy(element)
        
        # 移除已有的翻译内容
        for node in element_clone.find_all(attrs={"data-hfit-translation-element-mark": True}):
            node.decompose()
        
        # 标记所有子标签
        for tag in element_clone.find_all(True):
            tag['data-hfit-walked'] = self.session_id
        
        # 提取要翻译的纯文本
        texts_to_translate = []
        text_nodes = []
        
        # 递归查找所有文本节点
        self._find_text_nodes(element_clone, text_nodes)
        
        # 如果没有文本节点，直接返回
        if not text_nodes:
            return
        
        # 提取文本并准备翻译
        for node in text_nodes:
            text = node.string.strip()
            if text:
                texts_to_translate.append(text)
                
        # 批量翻译文本
        translated_texts = []
        if texts_to_translate:
            translated_texts = self.translation_service.translate_batch(texts_to_translate)
        
        # 用翻译后的文本替换原始文本
        for i, node in enumerate(text_nodes):
            if i < len(translated_texts):
                node.string.replace_with(translated_texts[i])
        
        # 创建并添加翻译包装器
        translated_content = element_clone.decode_contents()
        wrapper = self._create_translation_wrapper(translated_content)
        element.append(wrapper)
    
    def _translate_semantic_block_simple(self, element):
        """简单翻译语义块，不保留HTML结构
        
        这种方法只翻译纯文本内容，不保留标签结构。
        
        Args:
            element: 要翻译的HTML元素/语义块
        """
        # 标记段落已处理
        element['data-hfit-paragraph'] = '1'
        
        # 处理前检查元素是否已包含翻译
        if element.find(attrs={"data-hfit-translation-element-mark": "1"}):
            # 清除所有已存在的翻译标记，避免重复翻译
            for node in element.find_all(attrs={"data-hfit-translation-element-mark": "1"}):
                node.decompose()
        
        # 获取元素的纯文本内容
        text = element.get_text().strip()
        
        if not text:
            return
            
        # 翻译文本
        translated_text = self.translation_service.translate_text(text)
        
        # 创建并添加翻译包装器，启用深灰色样式
        wrapper = self._create_translation_wrapper(translated_text, is_simple_mode=True)
        element.append(wrapper)
    
    def _find_text_nodes(self, element, result):
        """递归查找所有文本节点
        
        Args:
            element: 要处理的HTML元素
            result: 收集文本节点的列表
        """
        for node in element.contents:
            if isinstance(node, NavigableString) and not isinstance(node, Comment):
                if node.strip():
                    result.append(node)
            elif isinstance(node, Tag):
                if node.name.upper() not in HTML_TAGS_NO_TRANSLATE:
                    self._find_text_nodes(node, result)
    
    def _translate_block(self, text_nodes, parent):
        """翻译单个语义块，生成并插入翻译
        
        Args:
            text_nodes: 文本节点列表
            parent: 父元素
        """
        if not text_nodes:
            return
        
        # 提取文本
        texts_to_translate = [node.string.strip() for node in text_nodes if node.string.strip()]
        if not texts_to_translate:
            return
        
        # 翻译文本
        translated_texts = self.translation_service.translate_batch(texts_to_translate)
        
        if not translated_texts:
            return
        
        # 创建翻译文本
        text_clone = ' '.join(translated_texts)
        
        # 创建并插入翻译包装器到最后一个文本节点后
        self._create_translation_wrapper(text_clone, text_nodes[-1])
       
    def _extract_semantic_blocks(self, paragraph):
        """从段落中提取待翻译的语义块
        
        提取最小语义块的新逻辑：
        1. 语义块是段落中从开头到其它段落标记的元素(或段落结尾)为止的位置范围内
        2. 包含全部文本节点的最小(最深)父节点
        3. 在提取过程中在结束位置增加一个占位符标记
        
        Args:
            paragraph: 要提取语义块的段落元素
            
        Returns:
            语义块列表，每个语义块是一个包含节点、最小公共祖先和结束标记的字典
        """
        semantic_blocks = []
        
        # 记录当前处理的文本节点
        current_text_nodes = []
        
        # 记录已经被处理过的元素
        processed_elements = set()
        
        # 递归遍历元素，收集语义块节点
        def collect_nodes(element, is_top_level=False):
            # 如果是带有段落标记的元素（除了顶级段落本身），结束当前语义块
            if not is_top_level and isinstance(element, Tag) and element.has_attr('data-hfit-paragraph'):
                # 结束当前语义块，处理收集到的文本节点
                if current_text_nodes:
                    finish_current_block(element)
                return  # 对于段落标记的元素，我们不处理其内容
            
            # 如果是文本节点，添加到当前块
            if isinstance(element, NavigableString) and not isinstance(element, Comment) and element.strip():
                current_text_nodes.append(element)
            
            # 递归处理子元素
            if isinstance(element, Tag):
                for child in element.children:
                    collect_nodes(child)
                    
                # 如果遍历完所有子元素后仍有未处理的文本节点，处理它们
                if not is_top_level and current_text_nodes and element.name.upper() not in HTML_TAGS_INLINE_TEXT:
                    finish_current_block(None)
        
        def finish_current_block(next_paragraph_element):
            """处理并完成当前语义块
            
            Args:
                next_paragraph_element: 下一个段落元素，如果没有则为None
            """
            nonlocal current_text_nodes, semantic_blocks, soup # Ensure soup is accessible
            
            if not current_text_nodes:
                return
                
            # 查找包含所有文本节点的最小公共祖先
            common_ancestor = find_minimum_common_ancestor(current_text_nodes)
            
            if common_ancestor:
                # Create end marker
                end_marker = soup.new_tag('span')
                end_marker['data-hfit-block-end-marker'] = '1'
                end_marker['style'] = 'display:none;'

                insert_location = None

                if next_paragraph_element:
                    # Insert before the start of the next paragraph block
                    next_paragraph_element.insert_before(end_marker)
                    insert_location = end_marker
                else:
                    # Block ends naturally (e.g., end of ancestor, or <br>)
                    # Find the actual last node relative to the common ancestor
                    if not current_text_nodes:
                         # Should not happen here, but safeguard
                         common_ancestor.append(end_marker)
                         insert_location = end_marker
                    else:
                        last_text = current_text_nodes[-1]
                        node_to_insert_after = last_text
                        # Traverse upwards from the last text node until we find the node
                        # that is a direct child of the common_ancestor, or None
                        while node_to_insert_after and node_to_insert_after.parent != common_ancestor:
                            node_to_insert_after = node_to_insert_after.parent
                            # Safety break if we somehow traverse outside the original paragraph scope
                            # This check might need refinement depending on exact DOM structure
                            if node_to_insert_after is None or node_to_insert_after.has_attr('data-hfit-paragraph'): 
                                node_to_insert_after = None # Invalid path found
                                break 

                        if node_to_insert_after and node_to_insert_after.parent == common_ancestor:
                             # Insert after the direct child of common_ancestor that contains the last text node
                             node_to_insert_after.insert_after(end_marker)
                             insert_location = end_marker
                        else:
                             # Fallback if traversal failed (e.g., text node was direct child, or structure is unexpected)
                             # If last_text itself is direct child, insert after it.
                             if last_text.parent == common_ancestor:
                                  last_text.insert_after(end_marker)
                                  insert_location = end_marker
                             else:
                                  # Ultimate fallback: append to common ancestor
                                  self.debug_print(f"[HTML处理] 警告: 无法定位精确插入点，将标记附加到公共祖先末尾。 祖先: {common_ancestor.name}, 最后文本父: {last_text.parent.name if last_text.parent else 'None'}")
                                  common_ancestor.append(end_marker)
                                  insert_location = end_marker

                # 创建语义块记录
                block = {
                    "nodes": current_text_nodes.copy(),
                    "common_ancestor": common_ancestor,
                    "end_marker": insert_location
                }
                
                semantic_blocks.append(block)
                
                # 清空当前文本节点列表
                current_text_nodes = []
        
        def find_minimum_common_ancestor(nodes):
            """查找一组节点的最小公共祖先
            
            Args:
                nodes: 节点列表
                
            Returns:
                最小公共祖先元素
            """
            if not nodes:
                return None
                
            if len(nodes) == 1:
                return nodes[0].parent
                
            # 获取第一个节点的所有祖先
            first_node = nodes[0]
            ancestors = []
            parent = first_node.parent
            
            while parent:
                ancestors.append(parent)
                parent = parent.parent
                
            # 对于每个后续节点，找到共同祖先
            common_ancestor = None
            
            for node in nodes[1:]:
                # 检查节点的每个祖先是否在ancestors列表中
                current = node.parent
                found = False
                
                while current and not found:
                    if current in ancestors:
                        # 找到共同祖先
                        common_ancestor = current
                        # 更新ancestors列表，只保留当前共同祖先及其祖先
                        idx = ancestors.index(current)
                        ancestors = ancestors[idx:]
                        found = True
                    current = current.parent
                    
                if not found:
                    # 如果没有找到共同祖先，返回None
                    return None
            
            return common_ancestor
            
        # 获取BeautifulSoup对象
        soup = paragraph.parent
        while soup.parent:
            soup = soup.parent
        
        # 开始从段落提取语义块
        collect_nodes(paragraph, True)
        
        # 处理最后一个语义块（如果有的话）
        if current_text_nodes:
            finish_current_block(None)
        
        return semantic_blocks
    
    def _process_paragraph(self, paragraph):
        """处理并翻译段落
        
        提取段落中的语义块，翻译每个语义块，并将翻译结果插入到原文中
        
        Args:
            paragraph: 要处理的段落元素
        """
        # 提取段落中的语义块
        semantic_blocks = self._extract_semantic_blocks(paragraph)
        
        # 如果没有语义块，直接返回
        if not semantic_blocks:
            return
        
        # 调试输出
        if self.debug:
            self.debug_print(f"[HTML处理] 在段落中找到 {len(semantic_blocks)} 个语义块")
        
        # 根据模式选择处理方法
        if self.preserve_tags_structure:
            # Advanced模式：保留HTML结构
            self._process_paragraph_advanced(paragraph, semantic_blocks)
        else:
            # Simple模式：只翻译纯文本
            self._process_paragraph_simple(paragraph, semantic_blocks)
    
    def _process_paragraph_simple(self, paragraph, semantic_blocks):
        """Simple模式处理段落（不保留HTML结构）
        
        Args:
            paragraph: 要处理的段落元素
            semantic_blocks: 提取的语义块列表
        """
        # 翻译每个语义块，不保留HTML结构
        for block in semantic_blocks:
            # 如果语义块中没有节点，跳过
            if not block["nodes"]:
                continue
            
            # 提取所有节点的文本，合并为一个完整的文本
            all_text = ""
            for node in block["nodes"]:
                if node.string and node.string.strip():
                    all_text += node.string.strip() + " "
            
            all_text = all_text.strip()
            
            # 如果没有文本需要翻译，跳过
            if not all_text:
                continue
                
            # 整体翻译文本
            translated_text = self.translation_service.translate_text(all_text)
            
            # 如果翻译失败，跳过
            if not translated_text:
                continue
            
            # 创建并插入翻译包装器到语义块结束标记位置，启用深灰色样式
            wrapper_element = self._create_translation_wrapper(translated_text, is_simple_mode=True)
            if block.get("end_marker"):
                block["end_marker"].insert_before(wrapper_element)
            # 注意: 如果没有end_marker，简单模式下目前不会插入翻译。可能需要增加回退逻辑。
    
    def _process_paragraph_advanced(self, paragraph, semantic_blocks):
        """Advanced模式处理段落（保留HTML结构）
        
        Args:
            paragraph: 要处理的段落元素
            semantic_blocks: 提取的语义块列表
        """
        # 这个函数在新的流程中不再直接调用，而是通过translate_html_content整体处理
        # 保留此函数以维持兼容性，但内部实现被移到了translate_html_content中
        pass
    
    def _is_ancestor(self, ancestor, descendant):
        """检查一个元素是否是另一个元素的祖先
        
        Args:
            ancestor: 可能的祖先元素
            descendant: 可能的后代元素
            
        Returns:
            布尔值，表示ancestor是否是descendant的祖先
        """
        parent = descendant.parent
        while parent:
            if parent == ancestor:
                return True
            parent = parent.parent
        return False
    
    def translate_html_content(self, html_content: str) -> str:
        """翻译HTML内容并返回双语版本
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            翻译后的HTML内容字符串
        """
        # 解析HTML
        self.debug_print(f"[HTML处理] 正在解析HTML...")
        parse_start = time.time()
        soup = BeautifulSoup(html_content, 'html.parser')
        parse_time = time.time() - parse_start
        self.debug_print(f"[HTML处理] HTML解析完成，耗时: {parse_time:.2f}秒")
        
        # 给html标签添加hfit-state属性
        html_tag = soup.find('html')
        if html_tag:
            html_tag['hfit-state'] = 'dual'
            self.debug_print(f"[HTML处理] 已设置HTML标签状态为双语显示")
            
        # 添加CSS样式
        self.debug_print(f"[HTML处理] 正在添加CSS样式...")
        self._add_styles(soup)
        
        # 给body添加唯一ID
        body = soup.find('body')
        if body:
            body['data-hfit-walked'] = self.session_id
            self.debug_print(f"[HTML处理] 已设置BODY标签唯一会话ID: {self.session_id[:8]}...")
        
        # 处理每个段落
        self.debug_print(f"[HTML处理] 正在分析段落...")
        find_start = time.time()
        paragraphs = self._find_paragraphs(soup)
        find_time = time.time() - find_start
        self.elements_count = len(paragraphs)
        self.debug_print(f"[HTML处理] 找到 {self.elements_count} 个段落，耗时: {find_time:.2f}秒")
        
        # 重置processed_count计数器
        self.processed_count = 0
        
        # 新增: 一次性收集所有需要翻译的文本
        self.debug_print(f"[HTML处理] 开始收集所有需要翻译的文本...")
        collect_start = time.time()
        
        # 用于存储所有需要翻译的文本和对应的原文
        all_texts_to_translate = []
        text_to_original_map = {}  # 用于存储文本与原文的映射关系
        processed_blocks = set()  # 用于记录已处理的语义块，避免重复处理
        
        # 从所有段落中提取需要翻译的文本
        for paragraph in paragraphs:
            # 获取段落预览
            text_preview = paragraph.get_text()[:50]
            if len(paragraph.get_text()) > 50:
                text_preview += "..."
                
            # 根据模式选择提取方法
            if self.preserve_tags_structure:
                # Advanced模式: 提取保留HTML结构的文本
                semantic_blocks = self._extract_semantic_blocks(paragraph)
                for block_index, block in enumerate(semantic_blocks):
                    # 创建一个唯一的块标识
                    block_id = f"{id(paragraph)}_{block_index}"
                    
                    # 如果这个块已经被处理过，跳过
                    if block_id in processed_blocks:
                        continue
                        
                    # 标记这个块已处理
                    processed_blocks.add(block_id)
                    
                    if not block["nodes"]:
                        continue
                        
                    # 高级模式提取文本
                    # 使用已经找到的最小公共祖先
                    common_ancestor = block["common_ancestor"]
                    
                    if common_ancestor:
                        # 复制共同祖先及其内容
                        ancestor_copy = copy.deepcopy(common_ancestor)
                        
                        # 找出需要保留的文本节点
                        nodes_to_keep = set(block["nodes"])
                        
                        # 清理不需要的节点
                        self._clean_copy_for_translation(ancestor_copy, nodes_to_keep)
                        
                        # 提取要翻译的纯文本
                        text_nodes = []
                        self._find_text_nodes(ancestor_copy, text_nodes)
                        
                        # 创建文本节点映射，用于应用翻译结果
                        node_map = {}
                        all_block_texts = []
                        
                        for node_index, node in enumerate(text_nodes):
                            text = node.string.strip()
                            if text:
                                # 为这个文本创建一个唯一ID
                                text_id = len(all_texts_to_translate)
                                node_map[text_id] = node
                                all_block_texts.append(text_id)
                                
                                # 添加到待翻译文本列表
                                all_texts_to_translate.append(text)
                        
                        # 如果有文本需要翻译，记录到映射中
                        if all_block_texts:
                            block_key = f"block_{block_id}"
                            text_to_original_map[block_key] = {
                                "type": "advanced_block",
                                "paragraph": paragraph,
                                "block": block,
                                "ancestor_copy": ancestor_copy,
                                "node_map": node_map,
                                "text_ids": all_block_texts
                            }
                    else:
                        # 如果找不到共同祖先，回退到简单模式
                        all_block_text = ""
                        for node in block["nodes"]:
                            if node.string and node.string.strip():
                                all_block_text += node.string.strip() + " "
                        
                        all_block_text = all_block_text.strip()
                        if all_block_text:
                            text_id = len(all_texts_to_translate)
                            all_texts_to_translate.append(all_block_text)
                            
                            block_key = f"block_{block_id}"
                            text_to_original_map[block_key] = {
                                "type": "simple_block",
                                "paragraph": paragraph,
                                "block": block,
                                "text_id": text_id
                            }
            else:
                # Simple模式: 只提取纯文本
                semantic_blocks = self._extract_semantic_blocks(paragraph)
                for block_index, block in enumerate(semantic_blocks):
                    # 创建一个唯一的块标识
                    block_id = f"{id(paragraph)}_{block_index}"
                    
                    # 如果这个块已经被处理过，跳过
                    if block_id in processed_blocks:
                        continue
                        
                    # 标记这个块已处理
                    processed_blocks.add(block_id)
                    
                    if not block["nodes"]:
                        continue
                        
                    # 提取所有节点的文本
                    all_text = ""
                    for node in block["nodes"]:
                        if node.string and node.string.strip():
                            all_text += node.string.strip() + " "
                    
                    all_text = all_text.strip()
                    if all_text:
                        text_id = len(all_texts_to_translate)
                        all_texts_to_translate.append(all_text)
                        
                        block_key = f"block_{block_id}"
                        text_to_original_map[block_key] = {
                            "type": "simple_block",
                            "paragraph": paragraph,
                            "block": block,
                            "text_id": text_id
                        }
        
        collect_time = time.time() - collect_start
        self.debug_print(f"[HTML处理] 共收集到 {len(all_texts_to_translate)} 个文本片段需要翻译，耗时: {collect_time:.2f}秒")
        
        # 一次性批量翻译所有文本
        if all_texts_to_translate:
            self.debug_print(f"[HTML处理] 开始批量翻译所有文本...")
            translate_start = time.time()
            all_translated_texts = self.translation_service.translate_batch(all_texts_to_translate)
            translate_time = time.time() - translate_start
            self.debug_print(f"[HTML处理] 翻译完成，翻译了 {len(all_translated_texts)} 个文本，耗时: {translate_time:.2f}秒")
        else:
            all_translated_texts = []
            self.debug_print(f"[HTML处理] 没有文本需要翻译")
        
        # 应用翻译结果到文档中
        self.debug_print(f"\n[HTML处理] 开始应用翻译结果...")
        apply_start = time.time()
        
        # 跟踪已处理的段落
        processed_paragraphs = set()
        
        # 实际应用翻译结果
        for i, (block_key, block_info) in enumerate(text_to_original_map.items()):
            # 显示进度
            progress = (i + 1) / len(text_to_original_map) * 100
            if i % 10 == 0 or i == len(text_to_original_map) - 1:  # 只在每10个或最后一个时显示进度
                self.debug_print(f"[HTML处理] 应用翻译进度: {progress:.1f}% ({i+1}/{len(text_to_original_map)})")
            
            block_type = block_info["type"]
            paragraph = block_info["paragraph"]
            block = block_info["block"]
            
            # 根据块类型处理翻译
            if block_type == "advanced_block":
                # 高级模式块
                ancestor_copy = block_info["ancestor_copy"]
                node_map = block_info["node_map"]
                text_ids = block_info["text_ids"]
                
                # 应用翻译到每个节点
                for text_id in text_ids:
                    if text_id < len(all_translated_texts):
                        node = node_map[text_id]
                        translated_text = all_translated_texts[text_id]
                        node.string.replace_with(translated_text)
                
                # 将处理后的HTML转为字符串
                translated_html = ancestor_copy.decode_contents()
                
                # 创建并插入翻译包装器到结束标记位置
                wrapper_element = self._create_translation_wrapper(translated_html)
                end_marker = block.get("end_marker")
                if end_marker:
                    end_marker.insert_before(wrapper_element)
                else:
                    # Fallback logic (e.g., append to paragraph? Log error?)
                    self.debug_print(f"[HTML处理] 警告: 块 {block_key} 缺少结束标记，尝试回退插入。")
                    # 使用 paragraph 作为回退插入点
                    paragraph.append(wrapper_element)
            elif block_type == "simple_block":
                # 简单模式块
                text_id = block_info["text_id"]
                if text_id < len(all_translated_texts):
                    translated_text = all_translated_texts[text_id]
                    wrapper_element = self._create_translation_wrapper(translated_text, is_simple_mode=True)
                    end_marker = block.get("end_marker")
                    if end_marker:
                        end_marker.insert_before(wrapper_element)
                    else:
                        # Fallback logic
                        self.debug_print(f"[HTML处理] 警告: 块 {block_key} 缺少结束标记，尝试回退插入。")
                        # 使用 paragraph 作为回退插入点
                        paragraph.append(wrapper_element)
            
            # 标记段落已处理
            paragraph['data-hfit-paragraph'] = '1'
            
            # 如果段落还没有被计数，则增加处理计数并将段落添加到已处理集合中
            if paragraph not in processed_paragraphs:
                processed_paragraphs.add(paragraph)
                self.processed_count += 1
        
        apply_time = time.time() - apply_start
        self.debug_print(f"[HTML处理] 应用翻译结果完成，耗时: {apply_time:.2f}秒")
        
        return str(soup)
    
    # Helper function for recursive cleaning
    def _clean_copy_recursive(self, element, nodes_to_keep_with_ancestors):
        """Recursively cleans children of an element."""
        nodes_to_remove = []
        for child in list(element.contents): # Iterate over a copy
            if child not in nodes_to_keep_with_ancestors:
                # If a child node (tag or non-empty text) is not in the keep set, mark for removal.
                # Also skip end markers during cleaning.
                if (isinstance(child, Tag) and not child.has_attr('data-hfit-block-end-marker')) or \
                   (isinstance(child, NavigableString) and child.strip()):
                     nodes_to_remove.append(child)
            elif isinstance(child, Tag) and not child.has_attr('data-hfit-block-end-marker'):
                 # If a tag is in the keep set (and not an end marker), recursively clean its children
                 self._clean_copy_recursive(child, nodes_to_keep_with_ancestors)

        # Remove marked nodes
        for node in nodes_to_remove:
            # Ensure it's still a direct child before removing
            if node.parent == element:
                 node.extract()

    def _clean_copy_for_translation(self, ancestor_copy, nodes_to_keep):
        """Clean the copied common ancestor to keep only the specified nodes and their parent tags."""
        nodes_to_keep_set = set(nodes_to_keep)
        nodes_to_keep_with_ancestors = set(nodes_to_keep_set)

        # Add all ancestors of the nodes_to_keep up to the ancestor_copy itself
        # Fix: Handle set access correctly
        if not nodes_to_keep_set:
            # If there are no nodes to keep, we shouldn't be here, but handle gracefully
            return

        # Get an arbitrary node to start ancestor traversal
        start_node = next(iter(nodes_to_keep_set))

        # The common ancestor logic should ideally happen before deepcopying,
        # or we need a robust way to map original nodes to copied nodes.
        # Sticking with the potentially flawed assumption for now to fix the TypeError.

        for node in nodes_to_keep_set:
            # Assuming nodes_to_keep contains references within ancestor_copy (POTENTIALLY WRONG)
            parent = node.parent
            while parent and parent != ancestor_copy.parent:
                nodes_to_keep_with_ancestors.add(parent)
                if parent == ancestor_copy:
                    break
                parent = parent.parent
        # Ensure ancestor_copy itself is included if it's an ancestor of any kept node
        # This check might be redundant if the above loop works correctly, but adds safety
        if any(self._is_ancestor(ancestor_copy, node) for node in nodes_to_keep_set):
             nodes_to_keep_with_ancestors.add(ancestor_copy)


        # Start the recursive cleaning from the ancestor_copy
        self._clean_copy_recursive(ancestor_copy, nodes_to_keep_with_ancestors)

        # Final pass to remove potentially empty containers that might remain
        self._clean_empty_tags(ancestor_copy)


    def _clean_empty_tags(self, element):
        """清理空标签
        
        Args:
            element: 要清理的元素
        """
        to_remove = []
        for child in element.contents:
            if isinstance(child, Tag):
                # 递归处理子元素
                self._clean_empty_tags(child)
                # 如果处理后变成空标签，标记删除
                if len(child.contents) == 0 or (len(child.contents) == 1 and 
                    isinstance(child.contents[0], NavigableString) and not child.contents[0].strip()):
                    to_remove.append(child)
        
        # 删除标记的元素
        for node in to_remove:
            node.extract() 