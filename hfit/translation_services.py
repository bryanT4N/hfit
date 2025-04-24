#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
hfit 的翻译服务模块

这个模块实现了翻译API服务:
1. 谷歌翻译API (免费版)
2. 微软(Bing)翻译 (免费版)
3. Yandex翻译 (免费版)
4. ArgosTranslate本地翻译 (离线版)
"""

import time
import json
import re
import urllib.parse
import requests
from typing import List, Optional
import sys
from bs4 import BeautifulSoup
from argostranslate import translate, package

# 谷歌翻译API请求头
GOOGLE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

# 微软(Bing)翻译获取参数请求头
BING_PARAMS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

# 微软(Bing)翻译API请求头
BING_TRANSLATE_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Origin': 'https://www.bing.com',
    'Referer': 'https://www.bing.com/translator',
}

# Yandex翻译获取参数请求头
YANDEX_PARAMS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# Yandex翻译API请求头
YANDEX_TRANSLATE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Referer': 'https://translate.yandex.com/',
    'Origin': 'https://translate.yandex.com',
    'Connection': 'keep-alive',
}

class TranslationService:
    """翻译服务的基类，定义了通用接口"""
    
    def __init__(self, source_language="en", target_language="zh-CN", debug=True):
        """初始化翻译服务
        
        Args:
            source_language: 源语言代码，默认为英语(en)
            target_language: 目标语言代码，默认为中文(zh-CN)
            debug: 是否显示调试信息
        """
        self.source_language = source_language
        self.target_language = target_language
        self.debug = debug
        self.translated_count = 0
        self.total_chars = 0
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """翻译一组文本
        
        Args:
            texts: 要翻译的文本列表
            
        Returns:
            翻译后的文本列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def translate_text(self, text: str) -> str:
        """翻译单个文本
        
        Args:
            text: 要翻译的文本
            
        Returns:
            翻译后的文本
        """
        if self.debug:
            print(f"[翻译] 正在翻译单个文本: {text[:30]}..." if len(text) > 30 else f"[翻译] 正在翻译单个文本: {text}")
        
        results = self.translate_batch([text])
        return results[0] if results else text

    def debug_print(self, message):
        """输出调试信息
        
        Args:
            message: 要输出的信息
        """
        if self.debug:
            print(message, flush=True)
            
    def format_progress(self, current, total, service_name="翻译服务", success=None, requests=None):
        """格式化进度信息，生成更直观的进度显示
        
        Args:
            current: 当前完成数量
            total: 总数量
            service_name: 服务名称
            success: 成功请求数
            requests: 总请求数
            
        Returns:
            格式化后的进度字符串
        """
        # 计算百分比
        percent = (current / total * 100) if total > 0 else 0
        
        # 创建一个简单的ASCII进度条(20个字符长度)
        bar_length = 20
        completed_length = int(bar_length * current / total) if total > 0 else 0
        progress_bar = '█' * completed_length + '░' * (bar_length - completed_length)
        
        # 格式化基本进度信息
        progress_info = f"[{service_name}] 翻译进度: [{progress_bar}] {percent:.1f}% ({current}/{total})"
        
        # 如果提供了成功率信息，添加到输出中
        if success is not None and requests is not None:
            success_rate = (success / requests * 100) if requests > 0 else 0
            progress_info += f" | 成功率: {success_rate:.1f}% ({success}/{requests})"

        progress_info += "\n"    
        return progress_info

    @staticmethod
    def escape_html(text: str) -> str:
        """HTML转义
        
        将 & < > " ' 转换为 &amp; &lt; &gt; &quot; &#39;
        
        Args:
            text: 要转义的文本
            
        Returns:
            转义后的文本
        """
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")
    
    @staticmethod
    def unescape_html(text: str) -> str:
        """HTML反转义
        
        将 &amp; &lt; &gt; &quot; &#39; 转换为 & < > " '
        
        Args:
            text: 要反转义的文本
            
        Returns:
            反转义后的文本
        """
        return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")


class GoogleTranslationService(TranslationService):
    """谷歌翻译API服务实现"""
    
    def __init__(self, source_language="en", target_language="zh-CN", debug=True):
        """初始化谷歌翻译服务
        
        Args:
            source_language: 源语言代码，默认为英语(en)
            target_language: 目标语言代码，默认为中文(zh-CN)
            debug: 是否显示调试信息
        """
        super().__init__(source_language, target_language, debug)
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
    def translate_batch(self, texts: List[str]) -> List[str]:
        """使用谷歌翻译网页接口翻译文本列表
        
        Args:
            texts: 要翻译的文本列表
            
        Returns:
            翻译后的文本列表
        """
        if not texts:
            return []
            
        batch_size = len(texts)
        total_chars = sum(len(text) for text in texts)
        self.debug_print(f"\n[谷歌翻译] 开始批量翻译 {batch_size} 个文本，共 {total_chars} 个字符")
        self.debug_print(f"[谷歌翻译] 从 {self.source_language} 翻译到 {self.target_language}")
        
        translations = []
        
        for i, text in enumerate(texts):
            try:
                # 显示进度
                progress = (i + 1) / batch_size * 100
                
                if not text.strip():
                    self.debug_print(f"[谷歌翻译] 跳过空文本")
                    translations.append("")
                    continue
                
                # 输出原文信息
                text_preview = text[:50] + "..." if len(text) > 50 else text
                self.debug_print(f"[谷歌翻译] 原文: {text_preview}")
                
                # 构建谷歌翻译API请求URL
                encoded_text = urllib.parse.quote(text)
                url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={self.target_language}&dt=t&q={encoded_text}"
                
                # 记录请求次数
                self.request_count += 1
                
                # 发送请求
                self.debug_print(f"[谷歌翻译] 发送请求 #{self.request_count}")
                start_time = time.time()
                response = requests.get(url, headers=GOOGLE_HEADERS)
                response.raise_for_status()
                elapsed_time = time.time() - start_time
                
                # 解析响应数据
                data = response.json()
                translated_text = ""
                
                # 提取翻译结果
                for sentence in data[0]:
                    if sentence[0]:
                        translated_text += sentence[0]
                
                # 记录成功次数
                self.success_count += 1
                self.translated_count += 1
                self.total_chars += len(text)
                
                # 输出翻译结果
                trans_preview = translated_text[:50] + "..." if len(translated_text) > 50 else translated_text
                self.debug_print(f"[谷歌翻译] 译文: {trans_preview}")
                self.debug_print(f"[谷歌翻译] 请求耗时: {elapsed_time:.2f}秒")
                
                translations.append(translated_text)
                
                # # 避免请求频率过高
                # if i < len(texts) - 1:  # 不是最后一个
                #     self.debug_print(f"[谷歌翻译] 等待100ms避免请求过于频繁...")
                #     time.sleep(0.1)
                
            except Exception as e:
                self.error_count += 1
                error_msg = f"谷歌翻译请求失败 ({self.error_count}/{self.request_count}): {str(e)}"
                self.debug_print(f"[错误] {error_msg}")
                # 失败时返回原文
                translations.append(text)
                
            # 更新进度条
            if self.debug and sys.stdout.isatty():
                sys.stdout.write("\r")
                sys.stdout.write(self.format_progress(
                    current=self.translated_count, 
                    total=batch_size, 
                    service_name="谷歌翻译", 
                    success=self.success_count, 
                    requests=self.request_count
                ))
                sys.stdout.flush()
        
        self.debug_print(f"\n[谷歌翻译] 批量翻译完成，成功: {self.success_count}/{self.request_count}")
        return translations


class BingTranslationService(TranslationService):
    """微软(Bing)翻译服务实现"""
    
    def __init__(self, source_language="en", target_language="zh-CN", debug=True):
        """初始化微软(Bing)翻译服务
        
        Args:
            source_language: 源语言代码，默认为英语(en)
            target_language: 目标语言代码，默认为中文(zh-CN)
            debug: 是否显示调试信息
        """
        super().__init__(source_language, target_language, debug)
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.translate_sid = None
        self.translate_iid_ig = None
        self.last_sid_fetch_time = 0
        self._fetch_lock = False
    
    def _find_sid(self):
        """查找Bing翻译所需的SID(参数)
        
        从Bing翻译页面获取必要参数，用于翻译请求
        """
        # 防止重复获取
        if self._fetch_lock:
            return
        
        self._fetch_lock = True
        current_time = time.time()
        
        # 检查是否需要更新SID
        if self.translate_sid and current_time - self.last_sid_fetch_time < 12 * 3600:  # 12小时有效期
            self._fetch_lock = False
            return
            
        try:
            self.debug_print(f"[微软翻译] 正在获取Bing翻译参数...")
            
            response = requests.get("https://www.bing.com/translator", headers=BING_PARAMS_HEADERS, timeout=10)
            response.raise_for_status()
            
            html_text = response.text
            
            # 调试输出页面内容片段
            if self.debug:
                snippet_size = 500
                html_snippet = html_text[:snippet_size] + "... [截断]" if len(html_text) > snippet_size else html_text
                self.debug_print(f"[微软翻译] 获取到页面内容片段:\n{html_snippet}")
                
                # 确认关键字搜索
                key_phrases = ["params_RichTranslateHelper", "data-iid", "IG:"]
                for phrase in key_phrases:
                    if phrase in html_text:
                        self.debug_print(f"[微软翻译] 页面包含关键字: {phrase}")
                    else:
                        self.debug_print(f"[微软翻译] 页面不包含关键字: {phrase}")
            
            # 使用更宽松的正则表达式
            params_match = re.search(r'params_[^=]+=\s*\[[^\]]+\]', html_text)
            data_iid_match = re.search(r'data-iid=[\"\']([^\"\']+)', html_text)
            ig_match = re.search(r'IG[\"\']?\s*:[\"\']?\s*([^\"\']+)', html_text)
            
            # 输出匹配结果
            if self.debug:
                self.debug_print(f"[微软翻译] params_match: {params_match.group(0) if params_match else 'None'}")
                self.debug_print(f"[微软翻译] data_iid_match: {data_iid_match.group(0) if data_iid_match else 'None'}")
                self.debug_print(f"[微软翻译] ig_match: {ig_match.group(0) if ig_match else 'None'}")
            
            # 尝试新的参数提取方式
            if html_text:
                # 先尝试第一种方式
                if params_match and data_iid_match and ig_match:
                    params_text = params_match.group(0)
                    params_parts = re.findall(r'[\d]+|"[^"]+"', params_text)
                    
                    data_iid = data_iid_match.group(1) if len(data_iid_match.groups()) >= 1 else data_iid_match.group(0).split('=')[1].strip('"\'')
                    ig = ig_match.group(1) if len(ig_match.groups()) >= 1 else ig_match.group(0).split(':')[1].strip('"\'')
                    
                    if len(params_parts) >= 2:
                        key = params_parts[0].strip('"\'')
                        token = params_parts[1].strip('"\'')
                        
                        self.translate_sid = f"&token={token}&key={key}"
                        self.translate_iid_ig = f"IG={ig}&IID={data_iid}"
                        self.last_sid_fetch_time = current_time
                        self.debug_print(f"[微软翻译] Bing翻译参数获取成功: {self.translate_sid[:20]}...")
                        self._fetch_lock = False
                        return
                
                # 尝试搜索COGNITIVE_SERVICES_ENDPOINT 和 API key
                msft_endpoint_match = re.search(r'COGNITIVE_SERVICES_ENDPOINT\s*=\s*[\"\']([^\"\']+)', html_text)
                msft_key_match = re.search(r'translatorApiKey\s*[:=]\s*[\"\']([^\"\']+)', html_text)
                
                if msft_endpoint_match and msft_key_match:
                    endpoint = msft_endpoint_match.group(1)
                    apikey = msft_key_match.group(1)
                    self.debug_print(f"[微软翻译] 找到Microsoft Translator API参数")
                    self.translate_sid = f"&key={apikey}"
                    self.translate_endpoint = endpoint
                    self.translate_iid_ig = "使用API"
                    self.last_sid_fetch_time = current_time
                    self._fetch_lock = False
                    return
            
            # 如果所有方法都失败，则不设置sid和iid，翻译会失败
            self.debug_print(f"[微软翻译] 无法获取有效的Bing翻译参数。")
            self.translate_sid = None
            self.translate_iid_ig = None
            self.last_sid_fetch_time = current_time
            self._fetch_lock = False
            return
            
        except Exception as e:
            self.debug_print(f"[错误] 获取Bing翻译参数失败: {str(e)}")
            self.translate_sid = None # Ensure reset on exception
            self.translate_iid_ig = None
        
        self._fetch_lock = False
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """使用微软(Bing)翻译网页接口翻译文本列表
        
        Args:
            texts: 要翻译的文本列表
            
        Returns:
            翻译后的文本列表
        """
        if not texts:
            return []
        
        # 获取必要参数
        self._find_sid()
        
        batch_size = len(texts)
        total_chars = sum(len(text) for text in texts)
        self.debug_print(f"\n[微软翻译] 开始批量翻译 {batch_size} 个文本，共 {total_chars} 个字符")
        self.debug_print(f"[微软翻译] 从 {self.source_language} 翻译到 {self.target_language}")
        
        # 根据目标语言调整语言代码
        source_lang = self._normalize_language_code(self.source_language)
        target_lang = self._normalize_language_code(self.target_language)
        
        translations = []
        
        # 正常使用Bing翻译参数
        if not self.translate_sid or not self.translate_iid_ig:
            self.debug_print(f"[微软翻译] 翻译参数未就绪，无法翻译")
            return texts  # 返回原文
        
        for i, text in enumerate(texts):
            try:
                # 显示进度
                progress = (i + 1) / batch_size * 100
                
                if not text.strip():
                    self.debug_print(f"[微软翻译] 跳过空文本")
                    translations.append("")
                    continue
                
                # 输出原文信息
                text_preview = text[:50] + "..." if len(text) > 50 else text
                self.debug_print(f"[微软翻译] 原文: {text_preview}")
                
                # 构建请求URL和数据
                url = f"https://www.bing.com/ttranslatev3?isVertical=1&{self.translate_iid_ig}"
                data = f"&fromLang={source_lang}&text={urllib.parse.quote(text)}&to={target_lang}{self.translate_sid}"
                
                # 记录请求次数
                self.request_count += 1
                
                # 发送请求
                self.debug_print(f"[微软翻译] 发送请求 #{self.request_count}")
                start_time = time.time()
                response = requests.post(url, data=data, headers=BING_TRANSLATE_HEADERS)
                
                # 添加错误处理
                if response.status_code != 200:
                    self.debug_print(f"[微软翻译] 请求返回状态码: {response.status_code}")
                    if self.debug:
                        self.debug_print(f"[微软翻译] 响应内容: {response.text[:200]}")
                    raise Exception(f"请求失败，状态码: {response.status_code}")
                    
                elapsed_time = time.time() - start_time
                
                # 解析响应数据
                try:
                    result = response.json()
                except:
                    self.debug_print(f"[微软翻译] 响应不是有效的JSON: {response.text[:100]}")
                    raise Exception("无法解析JSON响应")
                
                if result and len(result) > 0 and 'translations' in result[0] and len(result[0]['translations']) > 0:
                    translated_text = result[0]['translations'][0]['text']
                    
                    # 记录成功次数
                    self.success_count += 1
                    self.translated_count += 1
                    self.total_chars += len(text)
                    
                    # 输出翻译结果
                    trans_preview = translated_text[:50] + "..." if len(translated_text) > 50 else translated_text
                    self.debug_print(f"[微软翻译] 译文: {trans_preview}")
                    self.debug_print(f"[微软翻译] 请求耗时: {elapsed_time:.2f}秒")
                    
                    translations.append(translated_text)
                else:
                    self.debug_print(f"[微软翻译] 未获取到有效翻译结果")
                    self.debug_print(f"[微软翻译] 响应内容: {str(result)[:200]}")
                    translations.append(text)  # 返回原文
                
                ## 避免请求频率过高
                # if i < len(texts) - 1:  # 不是最后一个
                #     self.debug_print(f"[微软翻译] 等待100ms避免请求过于频繁...")
                #     time.sleep(0.1)
                
            except Exception as e:
                self.error_count += 1
                error_msg = f"微软翻译请求失败 ({self.error_count}/{self.request_count}): {str(e)}"
                self.debug_print(f"[错误] {error_msg}")
                # 失败时返回原文
                translations.append(text)
                
            # 更新进度条
            if self.debug and sys.stdout.isatty():
                sys.stdout.write("\r")
                sys.stdout.write(self.format_progress(
                    current=self.translated_count, 
                    total=batch_size, 
                    service_name="微软翻译", 
                    success=self.success_count, 
                    requests=self.request_count
                ))
                sys.stdout.flush()
        
        self.debug_print(f"\n[微软翻译] 批量翻译完成，成功: {self.success_count}/{self.request_count}")
        return translations
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """标准化语言代码
        
        将语言代码转换为Bing翻译支持的格式
        
        Args:
            lang_code: 语言代码
            
        Returns:
            标准化后的语言代码
        """
        # 语言代码映射表
        lang_map = {
            "auto": "auto-detect",
            "zh-CN": "zh-Hans",
            "zh-TW": "zh-Hant",
            "tl": "fil",
            "hmn": "mww",
            "ckb": "kmr",
            "mn": "mn-Cyrl",
            "no": "nb",
            "sr": "sr-Cyrl",
        }
        
        return lang_map.get(lang_code, lang_code)


class YandexTranslationService(TranslationService):
    """Yandex翻译服务实现"""
    
    def __init__(self, source_language="en", target_language="zh-CN", debug=True):
        """初始化Yandex翻译服务
        
        Args:
            source_language: 源语言代码，默认为英语(en)
            target_language: 目标语言代码，默认为中文(zh-CN)
            debug: 是否显示调试信息
        """
        super().__init__(source_language, target_language, debug)
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.translate_sid = None
        self.last_sid_fetch_time = 0
        self._fetch_lock = False
    
    def _find_sid(self):
        """查找Yandex翻译所需的SID(参数)
        
        从Yandex翻译页面获取必要参数，用于翻译请求
        """
        # 防止重复获取
        if self._fetch_lock:
            return
        
        self._fetch_lock = True
        current_time = time.time()
        
        # 检查是否需要更新SID
        if self.translate_sid and current_time - self.last_sid_fetch_time < 12 * 3600:  # 12小时有效期
            self._fetch_lock = False
            return
            
        try:
            self.debug_print(f"[Yandex翻译] 正在获取Yandex翻译参数...")
            
            response = requests.get("https://translate.yandex.net/website-widget/v1/widget.js?widgetId=ytWidget&pageLang=es&widgetTheme=light&autoMode=false", headers=YANDEX_PARAMS_HEADERS, timeout=10)
            response.raise_for_status()
            
            text = response.text
            sid_match = re.search(r'sid\:\s\'[0-9a-f\.]+', text)
            
            if sid_match and sid_match.group(0) and len(sid_match.group(0)) > 7:
                self.translate_sid = sid_match.group(0)[6:]
                self.last_sid_fetch_time = current_time
                self.debug_print(f"[Yandex翻译] 参数获取成功: {self.translate_sid[:10]}...")
                self._fetch_lock = False
                return
            
            self.debug_print(f"[Yandex翻译] 无法从Yandex翻译页面提取必要参数")
            
        except Exception as e:
            self.debug_print(f"[错误] 获取Yandex翻译参数失败: {str(e)}")
        
        self._fetch_lock = False
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """使用Yandex翻译网页接口翻译文本列表
        
        Args:
            texts: 要翻译的文本列表
            
        Returns:
            翻译后的文本列表
        """
        if not texts:
            return []
        
        # 获取必要参数
        self._find_sid()
        if not self.translate_sid:
            self.debug_print(f"[Yandex翻译] 翻译参数未就绪，无法翻译")
            return texts  # 返回原文
        
        batch_size = len(texts)
        total_chars = sum(len(text) for text in texts)
        self.debug_print(f"\n[Yandex翻译] 开始批量翻译 {batch_size} 个文本，共 {total_chars} 个字符")
        self.debug_print(f"[Yandex翻译] 从 {self.source_language} 翻译到 {self.target_language}")
        
        translations = []
        
        # 使用<wbr>标签连接多个文本，进行批量翻译
        # 也可以单独翻译每个文本，这里演示批量翻译
        joined_text = "<wbr>".join([self.escape_html(text) for text in texts])
        
        try:
            # 标准化语言代码
            source_lang = self.source_language
            target_lang = self.target_language
            
            # 中文需要特殊处理
            if source_lang.startswith("zh"):
                source_lang = "zh"
            if target_lang.startswith("zh"):
                target_lang = "zh"
            
            # 构建请求URL
            lang_param = f"{source_lang if source_lang != 'auto' else ''}-{target_lang}"
            if lang_param.startswith("-"):
                lang_param = lang_param[1:]
                
            url = f"https://translate.yandex.net/api/v1/tr.json/translate?srv=tr-url-widget&id={self.translate_sid}-0-0&format=html&lang={lang_param}&text={urllib.parse.quote(joined_text)}"
            
            # 记录请求次数
            self.request_count += 1
            
            # 发送请求
            self.debug_print(f"[Yandex翻译] 发送请求 #{self.request_count}")
            start_time = time.time()
            response = requests.get(url, headers=YANDEX_TRANSLATE_HEADERS)
            response.raise_for_status()
            elapsed_time = time.time() - start_time
            
            # 解析响应数据
            result = response.json()
            
            if result and 'text' in result and len(result['text']) > 0:
                # 获取检测到的语言
                detected_lang = result.get('lang', '').split('-')[0] if '-' in result.get('lang', '') else None
                
                # 获取翻译文本并拆分回列表
                translated_joined = result['text'][0]
                translated_items = translated_joined.split("<wbr>")
                
                # 反转义HTML
                translated_items = [self.unescape_html(item) for item in translated_items]
                
                # 处理返回结果数量不匹配的情况
                if len(translated_items) != len(texts):
                    self.debug_print(f"[警告] Yandex翻译返回的结果数量 ({len(translated_items)}) 与原文数量 ({len(texts)}) 不匹配")
                    # 如果数量不匹配，则尽可能填充，剩余的使用原文
                    if len(translated_items) < len(texts):
                        translated_items.extend(texts[len(translated_items):])
                    else:
                        translated_items = translated_items[:len(texts)]
                
                # 更新统计信息
                self.success_count += 1
                self.translated_count += batch_size
                self.total_chars += total_chars
                
                # 输出翻译结果预览
                self.debug_print(f"[Yandex翻译] 检测到的语言: {detected_lang or '未知'}")
                self.debug_print(f"[Yandex翻译] 翻译完成，耗时: {elapsed_time:.2f}秒")
                
                translations = translated_items
            else:
                self.debug_print(f"[Yandex翻译] 未获取到有效翻译结果")
                translations = texts  # 返回原文
                
        except Exception as e:
            self.error_count += 1
            error_msg = f"Yandex翻译请求失败 ({self.error_count}/{self.request_count}): {str(e)}"
            self.debug_print(f"[错误] {error_msg}")
            # 失败时返回原文
            translations = texts
            
        # 更新进度条
        if self.debug and sys.stdout.isatty():
            sys.stdout.write("\r")
            sys.stdout.write(self.format_progress(
                current=self.translated_count, 
                total=batch_size, 
                service_name="Yandex翻译", 
                success=self.success_count, 
                requests=self.request_count
            ))
            sys.stdout.flush()
        
        self.debug_print(f"\n[Yandex翻译] 批量翻译完成，成功: {self.success_count}/{self.request_count}")
        return translations


class ArgosTranslationService(TranslationService):
    """ArgosTranslate本地翻译服务实现"""
    
    def __init__(self, source_language="en", target_language="zh-CN", debug=True):
        """初始化ArgosTranslate本地翻译服务
        
        Args:
            source_language: 源语言代码，默认为英语(en)
            target_language: 目标语言代码，默认为中文(zh-CN)
            debug: 是否显示调试信息
        """
        super().__init__(source_language, target_language, debug)
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        
        # 规范化语言代码
        self.norm_source_language = self._normalize_language_code(source_language)
        self.norm_target_language = self._normalize_language_code(target_language)
        
        # 初始化时检查并安装所需的翻译包
        self._ensure_translation_package()
        
    def _normalize_language_code(self, lang_code: str) -> str:
        """标准化语言代码为ArgosTranslate支持的格式
        
        Args:
            lang_code: 语言代码
            
        Returns:
            标准化后的语言代码
        """
        # ArgosTranslate语言代码映射
        lang_map = {
            "zh-CN": "zh",
            "zh-TW": "zh",
            "en-US": "en",
            "en-GB": "en",
            "ja-JP": "ja",
            "ko-KR": "ko",
            "ru-RU": "ru",
            "de-DE": "de",
            "fr-FR": "fr",
            "es-ES": "es",
            "it-IT": "it",
            "pt-PT": "pt",
            "pt-BR": "pt"
        }
        
        # 对于包含'-'的语言代码，尝试获取主要部分
        if "-" in lang_code and lang_code not in lang_map:
            main_lang = lang_code.split("-")[0]
            return main_lang
            
        return lang_map.get(lang_code, lang_code)
    
    def _ensure_translation_package(self):
        """确保安装了所需的翻译包"""
        try:
            # 获取已安装的翻译包
            installed_packages = package.get_installed_packages()
            
            # 检查是否已经安装了所需的翻译包
            if not any(pkg.from_code == self.norm_source_language and pkg.to_code == self.norm_target_language for pkg in installed_packages):
                self.debug_print(f"[ArgosTranslate] 未找到翻译包 {self.norm_source_language} -> {self.norm_target_language}，尝试下载...")
                
                # 更新包索引
                package.update_package_index()
                available_packages = package.get_available_packages()
                
                # 查找合适的翻译包
                target_pkg = None
                for pkg in available_packages:
                    if pkg.from_code == self.norm_source_language and pkg.to_code == self.norm_target_language:
                        target_pkg = pkg
                        break
                
                if target_pkg:
                    self.debug_print(f"[ArgosTranslate] 正在下载翻译包 {self.norm_source_language} -> {self.norm_target_language}...")
                    download_path = target_pkg.download()
                    self.debug_print(f"[ArgosTranslate] 正在安装翻译包...")
                    package.install_from_path(download_path)
                    self.debug_print(f"[ArgosTranslate] 翻译包安装完成")
                else:
                    self.debug_print(f"[ArgosTranslate] 警告：未找到可用的翻译包 {self.norm_source_language} -> {self.norm_target_language}")
            else:
                self.debug_print(f"[ArgosTranslate] 已安装翻译包 {self.norm_source_language} -> {self.norm_target_language}")
                
        except Exception as e:
            self.debug_print(f"[ArgosTranslate] 初始化翻译包时出错: {str(e)}")
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        """使用ArgosTranslate本地翻译文本列表
        
        Args:
            texts: 要翻译的文本列表
            
        Returns:
            翻译后的文本列表
        """
        if not texts:
            return []
            
        batch_size = len(texts)
        total_chars = sum(len(text) for text in texts)
        self.debug_print(f"\n[ArgosTranslate] 开始批量翻译 {batch_size} 个文本，共 {total_chars} 个字符")
        self.debug_print(f"[ArgosTranslate] 从 {self.source_language} ({self.norm_source_language}) 翻译到 {self.target_language} ({self.norm_target_language})")
        
        translations = []
        
        for i, text in enumerate(texts):
            try:
                # 显示进度
                progress = (i + 1) / batch_size * 100
                
                if not text.strip():
                    self.debug_print(f"[ArgosTranslate] 跳过空文本")
                    translations.append("")
                    continue
                
                # 输出原文信息
                text_preview = text[:50] + "..." if len(text) > 50 else text
                self.debug_print(f"[ArgosTranslate] 原文: {text_preview}")
                
                # 记录请求次数
                self.request_count += 1
                
                # 执行翻译
                self.debug_print(f"[ArgosTranslate] 翻译请求 #{self.request_count}")
                start_time = time.time()
                translated_text = translate.translate(text, self.norm_source_language, self.norm_target_language)
                elapsed_time = time.time() - start_time
                
                # 记录成功次数
                self.success_count += 1
                self.translated_count += 1
                self.total_chars += len(text)
                
                # 输出翻译结果
                trans_preview = translated_text[:50] + "..." if len(translated_text) > 50 else translated_text
                self.debug_print(f"[ArgosTranslate] 译文: {trans_preview}")
                self.debug_print(f"[ArgosTranslate] 翻译耗时: {elapsed_time:.2f}秒")
                
                translations.append(translated_text)
                
            except Exception as e:
                self.error_count += 1
                error_msg = f"ArgosTranslate翻译请求失败 ({self.error_count}/{self.request_count}): {str(e)}"
                self.debug_print(f"[错误] {error_msg}")
                # 失败时返回原文
                translations.append(text)
                
            # 更新进度条
            if self.debug and sys.stdout.isatty():
                sys.stdout.write("\r")
                sys.stdout.write(self.format_progress(
                    current=self.translated_count, 
                    total=batch_size, 
                    service_name="ArgosTranslate", 
                    success=self.success_count, 
                    requests=self.request_count
                ))
                sys.stdout.flush()
        
        self.debug_print(f"\n[ArgosTranslate] 批量翻译完成，成功: {self.success_count}/{self.request_count}")
        return translations


def get_translation_service(service_name="google", source_language="en", target_language="zh-CN", debug=True):
    """工厂方法，根据名称创建对应的翻译服务实例
    
    Args:
        service_name: 翻译服务名称，支持'google'、'bing'、'yandex'、'argos'
        source_language: 源语言代码
        target_language: 目标语言代码
        debug: 是否显示调试信息
        
    Returns:
        TranslationService: 翻译服务实例
        
    Raises:
        ValueError: 如果指定的服务名称不支持
    """
    service_name = service_name.lower()
    
    if service_name == "google":
        return GoogleTranslationService(source_language, target_language, debug)
    elif service_name == "bing":
        return BingTranslationService(source_language, target_language, debug)
    elif service_name == "yandex":
        return YandexTranslationService(source_language, target_language, debug)
    elif service_name == "argos":
        return ArgosTranslationService(source_language, target_language, debug)
    else:
        raise ValueError(f"不支持的翻译服务: {service_name}。目前支持 'google'、'bing'、'yandex'、'argos'。") 