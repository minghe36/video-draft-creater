"""
DeepSeek API集成模块，用于智能文本纠错和结构化

该模块提供与DeepSeek Chat API的集成，用于：
- 纠正语法错误和拼写错误
- 优化标点符号
- 将文本结构化为逻辑段落
- 生成文本摘要
- 提取关键词
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """文本纠错结果"""
    original_text: str
    corrected_text: str
    model_used: str
    processing_time: float
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


@dataclass
class SummaryResult:
    """文本摘要结果"""
    original_text: str
    summary: str
    model_used: str
    processing_time: float
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


@dataclass
class KeywordsResult:
    """关键词提取结果"""
    original_text: str
    keywords: List[str]
    model_used: str
    processing_time: float
    tokens_used: Optional[int] = None
    cost: Optional[float] = None


@dataclass
class NLPAnalysisResult:
    """综合NLP分析结果"""
    original_text: str
    corrected_text: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    model_used: str = ""
    total_processing_time: float = 0.0
    total_tokens_used: Optional[int] = None
    total_cost: Optional[float] = None


class DeepSeekAPIError(Exception):
    """DeepSeek API相关错误"""
    pass


class TextCorrector:
    """DeepSeek API文本纠错器和NLP分析器"""
    
    DEFAULT_API_ENDPOINT = "https://api.deepseek.com/chat/completions"
    DEFAULT_MODEL = "deepseek-chat"
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_TIMEOUT = 30
    
    def __init__(
        self,
        api_key: str,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        model: str = DEFAULT_MODEL,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: int = DEFAULT_TIMEOUT
    ):
        """
        初始化文本纠错器和NLP分析器
        
        Args:
            api_key: DeepSeek API密钥
            api_endpoint: API端点URL
            model: 使用的模型名称
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        self.model = model
        self.timeout = timeout
        
        # 配置请求会话
        self.session = requests.Session()
        
        # 配置重试策略
        try:
            # 尝试新版本的参数名
            retry_strategy = Retry(
                total=max_retries,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST"],
                backoff_factor=1
            )
        except TypeError:
            # 回退到旧版本的参数名
            retry_strategy = Retry(
                total=max_retries,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "POST"],
                backoff_factor=1
            )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认headers
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        
        logger.info(f"TextCorrector初始化完成，使用模型: {self.model}")
    
    def _create_correction_prompt(self, text: str, language: str = "zh") -> str:
        """
        创建文本纠错提示词
        
        Args:
            text: 需要纠错的文本
            language: 文本语言 (zh: 中文, en: 英文)
            
        Returns:
            格式化的提示词
        """
        if language == "zh":
            prompt = f"""请对以下转录文本进行智能纠错和优化，包括：

1. 纠正语法错误、拼写错误和明显的转录错误
2. 添加适当的标点符号（逗号、句号、问号、感叹号等）来提高可读性
3. 将文本组织成逻辑清晰的段落
4. 保持原文的意思和语调不变
5. 如果是口语化表达，适当转换为书面语

请直接返回纠错后的文本，不要添加任何解释或说明：

{text}"""
        else:
            prompt = f"""Please intelligently correct and optimize the following transcribed text by:

1. Correcting grammatical errors, spelling mistakes, and obvious transcription errors
2. Adding appropriate punctuation (commas, periods, question marks, exclamation marks, etc.) to improve readability
3. Organizing the text into logical paragraphs
4. Maintaining the original meaning and tone
5. Converting colloquial expressions to written language where appropriate

Please return only the corrected text without any explanations:

{text}"""
        
        return prompt
    
    def _create_summary_prompt(self, text: str, language: str = "zh") -> str:
        """
        创建文本摘要提示词
        
        Args:
            text: 需要摘要的文本
            language: 文本语言 (zh: 中文, en: 英文)
            
        Returns:
            格式化的提示词
        """
        if language == "zh":
            prompt = f"""请为以下文本生成一个简洁而全面的摘要，要求：

1. 概括文本的主要内容和核心观点
2. 保持摘要的逻辑性和连贯性
3. 长度控制在原文的20-30%左右
4. 使用清晰简洁的语言
5. 保留重要的细节和关键信息

请直接返回摘要内容，不要添加任何解释或说明：

{text}"""
        else:
            prompt = f"""Please generate a concise and comprehensive summary of the following text with these requirements:

1. Capture the main content and core viewpoints
2. Maintain logical flow and coherence
3. Keep the length around 20-30% of the original text
4. Use clear and concise language
5. Preserve important details and key information

Please return only the summary without any explanations:

{text}"""
        
        return prompt
    
    def _create_keywords_prompt(self, text: str, language: str = "zh") -> str:
        """
        创建关键词提取提示词
        
        Args:
            text: 需要提取关键词的文本
            language: 文本语言 (zh: 中文, en: 英文)
            
        Returns:
            格式化的提示词
        """
        if language == "zh":
            prompt = f"""请从以下文本中提取最重要的关键词，要求：

1. 提取5-15个最具代表性的关键词或短语
2. 优先选择名词、专业术语和核心概念
3. 避免通用词汇（如"的"、"是"、"有"等）
4. 按重要性排序
5. 用逗号分隔关键词

请直接返回关键词列表，不要添加任何解释或说明：

{text}"""
        else:
            prompt = f"""Please extract the most important keywords from the following text with these requirements:

1. Extract 5-15 most representative keywords or phrases
2. Prioritize nouns, technical terms, and core concepts
3. Avoid common words (like "the", "is", "have", etc.)
4. Sort by importance
5. Separate keywords with commas

Please return only the keyword list without any explanations:

{text}"""
        
        return prompt
    
    def _make_api_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            messages: 消息列表
            
        Returns:
            API响应数据
            
        Raises:
            DeepSeekAPIError: API请求失败
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.1,  # 低温度确保一致性
            "max_tokens": 4000   # 足够的输出长度
        }
        
        try:
            logger.debug(f"发送API请求到: {self.api_endpoint}")
            response = self.session.post(
                self.api_endpoint,
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP错误: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
            except:
                error_msg += f" - {e.response.text}"
            
            logger.error(error_msg)
            raise DeepSeekAPIError(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"请求错误: {str(e)}"
            logger.error(error_msg)
            raise DeepSeekAPIError(error_msg)
    
    def correct_text(
        self,
        text: str,
        language: str = "zh",
        chunk_size: int = 2000
    ) -> CorrectionResult:
        """
        纠错文本
        
        Args:
            text: 需要纠错的文本
            language: 文本语言 (zh: 中文, en: 英文)
            chunk_size: 文本分块大小（避免超出API限制）
            
        Returns:
            纠错结果
            
        Raises:
            DeepSeekAPIError: API调用失败
        """
        if not text.strip():
            return CorrectionResult(
                original_text=text,
                corrected_text=text,
                model_used=self.model,
                processing_time=0.0
            )
        
        start_time = time.time()
        logger.info(f"开始纠错文本，长度: {len(text)} 字符")
        
        try:
            # 如果文本太长，分块处理
            if len(text) > chunk_size:
                return self._correct_text_in_chunks(text, language, chunk_size)
            
            # 创建提示词
            prompt = self._create_correction_prompt(text, language)
            messages = [{"role": "user", "content": prompt}]
            
            # 发送API请求
            response_data = self._make_api_request(messages)
            
            # 提取纠错后的文本
            corrected_text = response_data["choices"][0]["message"]["content"].strip()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 提取使用信息
            usage = response_data.get("usage", {})
            tokens_used = usage.get("total_tokens")
            
            logger.info(f"文本纠错完成，耗时: {processing_time:.2f}秒，使用tokens: {tokens_used}")
            
            return CorrectionResult(
                original_text=text,
                corrected_text=corrected_text,
                model_used=self.model,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"文本纠错失败: {str(e)}")
            raise
    
    def _correct_text_in_chunks(
        self,
        text: str,
        language: str,
        chunk_size: int
    ) -> CorrectionResult:
        """
        分块纠错长文本
        
        Args:
            text: 需要纠错的文本
            language: 文本语言
            chunk_size: 每块大小
            
        Returns:
            纠错结果
        """
        logger.info(f"文本过长，将分块处理，块大小: {chunk_size}")
        
        # 按句子分割文本，避免在句子中间截断
        sentences = self._split_into_sentences(text, language)
        chunks = self._group_sentences_into_chunks(sentences, chunk_size)
        
        corrected_chunks = []
        total_tokens = 0
        start_time = time.time()
        
        for i, chunk in enumerate(chunks):
            logger.debug(f"处理第 {i+1}/{len(chunks)} 块")
            
            result = self.correct_text(chunk, language, chunk_size * 2)  # 递归调用，增大块大小避免无限递归
            corrected_chunks.append(result.corrected_text)
            
            if result.tokens_used:
                total_tokens += result.tokens_used
            
            # 避免API限流
            if i < len(chunks) - 1:
                time.sleep(1)
        
        # 合并所有块
        corrected_text = "\n\n".join(corrected_chunks)
        processing_time = time.time() - start_time
        
        return CorrectionResult(
            original_text=text,
            corrected_text=corrected_text,
            model_used=self.model,
            processing_time=processing_time,
            tokens_used=total_tokens
        )
    
    def summarize_text(
        self,
        text: str,
        language: str = "zh"
    ) -> SummaryResult:
        """
        生成文本摘要
        
        Args:
            text: 需要摘要的文本
            language: 文本语言 (zh: 中文, en: 英文)
            
        Returns:
            摘要结果
            
        Raises:
            DeepSeekAPIError: API调用失败
        """
        if not text.strip():
            return SummaryResult(
                original_text=text,
                summary="",
                model_used=self.model,
                processing_time=0.0
            )
        
        start_time = time.time()
        logger.info(f"开始生成摘要，文本长度: {len(text)} 字符")
        
        try:
            # 创建摘要提示词
            prompt = self._create_summary_prompt(text, language)
            messages = [{"role": "user", "content": prompt}]
            
            # 发送API请求
            response_data = self._make_api_request(messages)
            
            # 提取摘要
            summary = response_data["choices"][0]["message"]["content"].strip()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 提取使用信息
            usage = response_data.get("usage", {})
            tokens_used = usage.get("total_tokens")
            
            logger.info(f"摘要生成完成，耗时: {processing_time:.2f}秒，使用tokens: {tokens_used}")
            
            return SummaryResult(
                original_text=text,
                summary=summary,
                model_used=self.model,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"摘要生成失败: {str(e)}")
            raise
    
    def extract_keywords(
        self,
        text: str,
        language: str = "zh"
    ) -> KeywordsResult:
        """
        提取关键词
        
        Args:
            text: 需要提取关键词的文本
            language: 文本语言 (zh: 中文, en: 英文)
            
        Returns:
            关键词提取结果
            
        Raises:
            DeepSeekAPIError: API调用失败
        """
        if not text.strip():
            return KeywordsResult(
                original_text=text,
                keywords=[],
                model_used=self.model,
                processing_time=0.0
            )
        
        start_time = time.time()
        logger.info(f"开始提取关键词，文本长度: {len(text)} 字符")
        
        try:
            # 创建关键词提取提示词
            prompt = self._create_keywords_prompt(text, language)
            messages = [{"role": "user", "content": prompt}]
            
            # 发送API请求
            response_data = self._make_api_request(messages)
            
            # 提取关键词
            keywords_text = response_data["choices"][0]["message"]["content"].strip()
            
            # 解析关键词列表
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            
            # 计算处理时间
            processing_time = time.time() - start_time
            
            # 提取使用信息
            usage = response_data.get("usage", {})
            tokens_used = usage.get("total_tokens")
            
            logger.info(f"关键词提取完成，耗时: {processing_time:.2f}秒，使用tokens: {tokens_used}，提取到 {len(keywords)} 个关键词")
            
            return KeywordsResult(
                original_text=text,
                keywords=keywords,
                model_used=self.model,
                processing_time=processing_time,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"关键词提取失败: {str(e)}")
            raise
    
    def analyze_text(
        self,
        text: str,
        language: str = "zh",
        include_correction: bool = True,
        include_summary: bool = True,
        include_keywords: bool = True
    ) -> NLPAnalysisResult:
        """
        综合文本分析（纠错、摘要、关键词提取）
        
        Args:
            text: 需要分析的文本
            language: 文本语言 (zh: 中文, en: 英文)
            include_correction: 是否包含文本纠错
            include_summary: 是否包含摘要生成
            include_keywords: 是否包含关键词提取
            
        Returns:
            综合分析结果
            
        Raises:
            DeepSeekAPIError: API调用失败
        """
        if not text.strip():
            return NLPAnalysisResult(
                original_text=text,
                model_used=self.model
            )
        
        start_time = time.time()
        logger.info(f"开始综合文本分析，文本长度: {len(text)} 字符")
        
        result = NLPAnalysisResult(
            original_text=text,
            model_used=self.model
        )
        
        total_tokens = 0
        
        try:
            # 文本纠错
            if include_correction:
                logger.info("执行文本纠错...")
                correction_result = self.correct_text(text, language)
                result.corrected_text = correction_result.corrected_text
                if correction_result.tokens_used:
                    total_tokens += correction_result.tokens_used
                
                # 使用纠错后的文本进行后续分析
                analysis_text = correction_result.corrected_text
            else:
                analysis_text = text
            
            # 生成摘要
            if include_summary:
                logger.info("生成文本摘要...")
                summary_result = self.summarize_text(analysis_text, language)
                result.summary = summary_result.summary
                if summary_result.tokens_used:
                    total_tokens += summary_result.tokens_used
            
            # 提取关键词
            if include_keywords:
                logger.info("提取关键词...")
                keywords_result = self.extract_keywords(analysis_text, language)
                result.keywords = keywords_result.keywords
                if keywords_result.tokens_used:
                    total_tokens += keywords_result.tokens_used
            
            # 计算总处理时间
            result.total_processing_time = time.time() - start_time
            result.total_tokens_used = total_tokens
            
            logger.info(f"综合文本分析完成，总耗时: {result.total_processing_time:.2f}秒，总tokens: {total_tokens}")
            
            return result
            
        except Exception as e:
            logger.error(f"综合文本分析失败: {str(e)}")
            raise
    
    def _split_into_sentences(self, text: str, language: str) -> List[str]:
        """
        将文本分割为句子
        
        Args:
            text: 输入文本
            language: 语言
            
        Returns:
            句子列表
        """
        import re
        
        if language == "zh":
            # 中文句子分割
            pattern = r'[。！？；\n]+'
        else:
            # 英文句子分割
            pattern = r'[.!?;\n]+'
        
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _group_sentences_into_chunks(self, sentences: List[str], max_chunk_size: int) -> List[str]:
        """
        将句子组合成块
        
        Args:
            sentences: 句子列表
            max_chunk_size: 最大块大小
            
        Returns:
            文本块列表
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            # 如果当前块加上这个句子会超出限制，则开始新块
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # 添加最后一块
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def batch_correct_texts(
        self,
        texts: List[str],
        language: str = "zh",
        delay_between_requests: float = 1.0
    ) -> List[CorrectionResult]:
        """
        批量纠错文本
        
        Args:
            texts: 文本列表
            language: 语言
            delay_between_requests: 请求间延迟（秒）
            
        Returns:
            纠错结果列表
        """
        results = []
        
        for i, text in enumerate(texts):
            logger.info(f"批量处理进度: {i+1}/{len(texts)}")
            
            try:
                result = self.correct_text(text, language)
                results.append(result)
                
                # 避免API限流
                if i < len(texts) - 1:
                    time.sleep(delay_between_requests)
                    
            except Exception as e:
                logger.error(f"处理第 {i+1} 个文本时出错: {str(e)}")
                # 创建错误结果
                error_result = CorrectionResult(
                    original_text=text,
                    corrected_text=text,  # 失败时返回原文
                    model_used=self.model,
                    processing_time=0.0
                )
                results.append(error_result)
        
        return results
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            test_text = "这是一个测试。" if "zh" in self.model else "This is a test."
            result = self.correct_text(test_text)
            logger.info("API连接测试成功")
            return True
            
        except Exception as e:
            logger.error(f"API连接测试失败: {str(e)}")
            return False


def create_corrector_from_config(config) -> TextCorrector:
    """
    从配置创建文本纠错器
    
    Args:
        config: 配置对象或字典
        
    Returns:
        文本纠错器实例
    """
    # 处理不同类型的配置输入
    if hasattr(config, 'get'):  # 字典类型
        correction_config = config.get("correction", {})
        api_key = correction_config.get("api_key")
        api_endpoint = correction_config.get("api_endpoint", TextCorrector.DEFAULT_API_ENDPOINT)
        model = correction_config.get("model", TextCorrector.DEFAULT_MODEL)
        max_retries = correction_config.get("max_retries", TextCorrector.DEFAULT_MAX_RETRIES)
        timeout = correction_config.get("timeout", TextCorrector.DEFAULT_TIMEOUT)
    else:  # 配置对象类型
        api_key = getattr(config, 'api_key', None)
        api_endpoint = getattr(config, 'api_endpoint', TextCorrector.DEFAULT_API_ENDPOINT)
        model = getattr(config, 'model', TextCorrector.DEFAULT_MODEL)
        max_retries = getattr(config, 'max_retries', TextCorrector.DEFAULT_MAX_RETRIES)
        timeout = getattr(config, 'timeout', TextCorrector.DEFAULT_TIMEOUT)
    
    if not api_key:
        raise ValueError("未找到DeepSeek API密钥，请在配置中设置correction.api_key")
    
    return TextCorrector(
        api_key=api_key,
        api_endpoint=api_endpoint,
        model=model,
        max_retries=max_retries,
        timeout=timeout
    ) 