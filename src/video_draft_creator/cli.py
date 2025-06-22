"""
命令行界面
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import List, Optional
import yaml

from .config import load_config, Config
from .downloader import create_downloader
from .transcriber import create_transcriber, TranscriptionError
from .corrector import create_corrector_from_config, DeepSeekAPIError
from .output_formatter import create_formatter, DocumentMetadata, DocumentFormatterError
from .progress import StatusDisplay, EnhancedProgress, create_progress_callback
from .config_manager import (
    get_config_manager, 
    save_current_config_as_profile, 
    load_config_profile,
    list_config_profiles,
    delete_config_profile
)


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """设置日志"""
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # 创建日志目录
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 配置根日志
    logging.basicConfig(
        level=numeric_level,
        handlers=[console_handler] + ([logging.FileHandler(log_file)] if log_file else []),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


# 全局变量用于进度显示
_verbose_mode = False


def set_verbose_mode(verbose: bool):
    """设置详细模式"""
    global _verbose_mode
    _verbose_mode = verbose


def get_progress_callback(operation_type: str):
    """获取适合的进度回调函数"""
    return create_progress_callback(operation_type, _verbose_mode)


def cmd_process(args):
    """处理单个URL"""
    # 设置详细模式
    set_verbose_mode(getattr(args, 'verbose', False))
    
    # 创建进度跟踪器
    progress = EnhancedProgress(_verbose_mode)
    
    try:
        # 步骤1: 加载配置
        progress.start_operation("加载配置")
        
        # 如果指定了profile，先加载profile配置
        config = None
        if getattr(args, 'profile', None):
            config = load_config_profile(args.profile)
            if config is None:
                StatusDisplay.error(f"配置预设不存在: {args.profile}")
                return False
            progress.update_operation(f"已加载配置预设: {args.profile}")
        
        # 加载基础配置
        if config is None:
            config = load_config(args.config)
        
        # 从命令行参数覆盖配置
        if args.output_dir:
            config.download.output_dir = args.output_dir
        if args.audio_quality:
            config.download.audio_quality = args.audio_quality
        if args.cookie_browser:
            config.download.cookies.from_browser = args.cookie_browser
        if args.cookie_file:
            config.download.cookies.cookie_file = args.cookie_file
        
        progress.complete_operation("配置加载完成")
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 步骤2: 初始化下载器
        progress.start_operation("初始化下载器")
        downloader = create_downloader()
        downloader.config = config
        progress.complete_operation("下载器初始化完成")
        
        # 步骤3: 验证URL
        progress.start_operation("验证URL")
        supported, platform = downloader.check_url_support(args.url)
        if not supported:
            StatusDisplay.error(f"不支持的平台", platform, [
                "检查URL格式是否正确",
                "确认平台是否受支持",
                "查看文档了解支持的平台列表"
            ])
            return False
        
        progress.update_operation(f"检测到平台: {platform}")
        progress.complete_operation("URL验证完成")
        
        # 获取视频信息
        if args.info_only:
            progress.start_operation("获取视频信息")
            info = downloader.get_video_info(args.url)
            if info:
                StatusDisplay.success("视频信息获取成功")
                StatusDisplay.info("视频详情", f"""
标题: {info['title']}
时长: {info['duration']}秒
上传者: {info['uploader']}
平台: {info['platform']}
播放量: {info['view_count']:,}""" if info['view_count'] else "")
                progress.complete_operation()
            else:
                StatusDisplay.error("无法获取视频信息", "可能需要cookie验证", [
                    "使用 --cookie-browser chrome 选项",
                    "使用 --cookie-file cookies.txt 选项",
                    "检查配置文件中的cookie设置"
                ])
                progress.fail_operation("获取视频信息失败")
            return True
        
        # 步骤4: 下载音频
        progress.start_operation("下载音频")
        progress_callback = get_progress_callback("download")
        
        success, message, file_path = downloader.download_audio(
            args.url, 
            args.output_name,
            progress_callback
        )
        
        if success:
            StatusDisplay.success("音频下载完成", f"文件位置: {file_path}")
            progress.complete_operation()
            
            # 转录处理
            if args.transcribe:
                transcribe_success = perform_transcription(file_path, config, args)
                if not transcribe_success:
                    StatusDisplay.error("转录处理失败")
                    return False
            
            return True
        else:
            error_suggestions = []
            if "cookie" in message.lower() or "验证" in message.lower():
                error_suggestions = [
                    "使用浏览器cookie: --cookie-browser chrome",
                    "使用cookie文件: --cookie-file cookies.txt",
                    "检查配置文件中的cookie设置"
                ]
            
            StatusDisplay.error("下载失败", message, error_suggestions)
            progress.fail_operation(message, error_suggestions)
            return False
            
    except Exception as e:
        StatusDisplay.error("处理失败", str(e), [
            "检查网络连接",
            "验证URL是否有效",
            "查看日志文件获取详细错误信息"
        ])
        progress.fail_operation(str(e))
        return False


def perform_transcription(audio_file: str, config: Config, args) -> bool:
    """执行音频转录"""
    try:
        audio_path = Path(audio_file)
        if not audio_path.exists():
            print(f"❌ 音频文件不存在: {audio_file}")
            return False
        
        # 创建转录器
        transcriber = create_transcriber(
            model_size=config.transcription.model_size,
            device="auto",
            compute_type="auto"
        )
        
        # 设置输出目录
        output_dir = audio_path.parent
        if hasattr(args, 'output_dir') and args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置语言
        language = config.transcription.language if config.transcription.language != 'auto' else None
        
        print(f"🔄 正在转录: {audio_path.name}")
        print(f"📋 模型: {config.transcription.model_size}")
        print(f"🌍 语言: {language or '自动检测'}")
        
        # 进度回调
        def transcription_progress(segment_count, segment):
            print(f"\r🎙️ 已处理: {segment_count} 段", end='', flush=True)
        
        # 执行转录
        result = transcriber.transcribe_audio(
            audio_path,
            language=language,
            beam_size=config.transcription.beam_size,
            temperature=config.transcription.temperature,
            progress_callback=transcription_progress
        )
        
        print(f"\n📊 转录完成:")
        print(f"  🌍 检测语言: {result.language} ({result.language_probability:.2f})")
        print(f"  ⏱️ 音频时长: {result.duration:.2f}秒")
        print(f"  📝 文本段数: {len(result.segments)}")
        
        # 生成输出文件
        base_name = audio_path.stem
        
        # 生成字幕文件
        srt_path = output_dir / f"{base_name}.srt"
        transcriber.generate_srt(result, srt_path)
        print(f"📄 SRT字幕: {srt_path}")
        
        vtt_path = output_dir / f"{base_name}.vtt"
        transcriber.generate_vtt(result, vtt_path)
        print(f"📄 VTT字幕: {vtt_path}")
        
        # 生成纯文本
        txt_path = output_dir / f"{base_name}_transcript.txt"
        transcriber.generate_text(result, txt_path)
        print(f"📄 转录文本: {txt_path}")
        
        # 显示文本预览
        preview_length = 200
        if len(result.text) > preview_length:
            preview = result.text[:preview_length] + "..."
        else:
            preview = result.text
        
        print(f"\n📝 原始转录预览:")
        print(f"「{preview}」")
        
        # 文本纠错处理
        final_text = result.text
        if hasattr(args, 'correct') and args.correct:
            print(f"\n🤖 开始文本纠错...")
            corrected_text = perform_correction(result.text, output_dir, base_name, config, result.language)
            if corrected_text:
                print("✅ 文本纠错完成")
                final_text = corrected_text
            else:
                print("❌ 文本纠错失败，使用原始转录文本")
        
        # 摘要生成处理
        if hasattr(args, 'summarize') and args.summarize:
            print(f"\n📝 开始生成摘要...")
            summarization_success = perform_summarization(final_text, output_dir, base_name, config, result.language)
            if summarization_success:
                print("✅ 摘要生成完成")
            else:
                print("❌ 摘要生成失败")
        
        # 关键词提取处理
        if hasattr(args, 'keywords') and args.keywords:
            print(f"\n🔍 开始提取关键词...")
            keywords_success = perform_keywords_extraction(final_text, output_dir, base_name, config, result.language)
            if keywords_success:
                print("✅ 关键词提取完成")
            else:
                print("❌ 关键词提取失败")
        
        # 文档格式化处理
        if hasattr(args, 'format') and args.format:
            print(f"\n📝 开始生成格式化文档...")
            formats = [args.format] if isinstance(args.format, str) else args.format
            source_info = f"音频文件: {audio_path.name}"
            
            formatting_success = perform_document_formatting(
                content=final_text,
                output_dir=output_dir,
                base_name=f"{base_name}_formatted",
                formats=formats,
                config=config,
                source_info=source_info
            )
            
            if formatting_success:
                print("✅ 文档格式化完成")
            else:
                print("❌ 文档格式化失败")
        
        return True
        
    except TranscriptionError as e:
        print(f"❌ 转录失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 转录过程出错: {e}")
        return False


def perform_correction(text: str, output_dir: Path, base_name: str, config: Config, language: str) -> bool:
    """执行文本纠错"""
    try:
        # 检查是否配置了API密钥
        if not hasattr(config, 'correction') or not config.correction.api_key:
            print("❌ 未配置DeepSeek API密钥，跳过文本纠错")
            print("💡 请在配置文件中设置correction.api_key")
            return False
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.to_dict())
        
        # 测试API连接
        print("🔍 测试API连接...")
        if not corrector.test_connection():
            print("❌ API连接测试失败")
            return False
        
        print("✅ API连接正常")
        
        # 确定语言
        correction_language = "zh" if language in ["zh", "chinese"] else "en"
        
        print(f"🔄 正在纠错文本...")
        print(f"📋 语言: {correction_language}")
        print(f"📏 原文长度: {len(text)} 字符")
        
        # 执行纠错
        result = corrector.correct_text(text, language=correction_language)
        
        print(f"📊 纠错完成:")
        print(f"  ⏱️ 处理时间: {result.processing_time:.2f}秒")
        print(f"  🎯 使用模型: {result.model_used}")
        if result.tokens_used:
            print(f"  🔢 使用Tokens: {result.tokens_used}")
        
        # 保存纠错后的文本
        corrected_path = output_dir / f"{base_name}_corrected.txt"
        with open(corrected_path, 'w', encoding='utf-8') as f:
            f.write(result.corrected_text)
        
        print(f"📄 纠错文本: {corrected_path}")
        
        # 显示纠错后的预览
        preview_length = 200
        if len(result.corrected_text) > preview_length:
            corrected_preview = result.corrected_text[:preview_length] + "..."
        else:
            corrected_preview = result.corrected_text
        
        print(f"\n📝 纠错后预览:")
        print(f"「{corrected_preview}」")
        
        # 生成对比文件（可选）
        comparison_path = output_dir / f"{base_name}_comparison.txt"
        with open(comparison_path, 'w', encoding='utf-8') as f:
            f.write("=== 原始转录 ===\n\n")
            f.write(result.original_text)
            f.write("\n\n=== 纠错后文本 ===\n\n")
            f.write(result.corrected_text)
            f.write(f"\n\n=== 处理信息 ===\n")
            f.write(f"处理时间: {result.processing_time:.2f}秒\n")
            f.write(f"使用模型: {result.model_used}\n")
            if result.tokens_used:
                f.write(f"使用Tokens: {result.tokens_used}\n")
        
        print(f"📄 对比文件: {comparison_path}")
        
        return result.corrected_text
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 文本纠错过程出错: {e}")
        return False


def perform_summarization(text: str, output_dir: Path, base_name: str, config: Config, language: str) -> bool:
    """执行文本摘要"""
    try:
        # 检查是否配置了API密钥
        if not hasattr(config, 'correction') or not config.correction.api_key:
            print("❌ 未配置DeepSeek API密钥，跳过文本摘要")
            print("💡 请在配置文件中设置correction.api_key")
            return False
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.correction)
        
        # 确定语言
        summary_language = "zh" if language in ["zh", "chinese"] else "en"
        
        print(f"🔄 正在生成摘要...")
        print(f"📋 语言: {summary_language}")
        print(f"📏 原文长度: {len(text)} 字符")
        
        # 执行摘要
        result = corrector.summarize_text(text, language=summary_language)
        
        print(f"📊 摘要生成完成:")
        print(f"  ⏱️ 处理时间: {result.processing_time:.2f}秒")
        print(f"  🎯 使用模型: {result.model_used}")
        if result.tokens_used:
            print(f"  🔢 使用Tokens: {result.tokens_used}")
        
        # 保存摘要
        summary_path = output_dir / f"{base_name}_summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(result.summary)
        
        print(f"📄 摘要文件: {summary_path}")
        
        # 显示摘要预览
        preview_length = 200
        preview = result.summary[:preview_length] + "..." if len(result.summary) > preview_length else result.summary
        print(f"\n📝 摘要预览:")
        print(f"「{preview}」")
        
        return True
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 摘要生成过程出错: {e}")
        return False


def perform_keywords_extraction(text: str, output_dir: Path, base_name: str, config: Config, language: str) -> bool:
    """执行关键词提取"""
    try:
        # 检查是否配置了API密钥
        if not hasattr(config, 'correction') or not config.correction.api_key:
            print("❌ 未配置DeepSeek API密钥，跳过关键词提取")
            print("💡 请在配置文件中设置correction.api_key")
            return False
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.correction)
        
        # 确定语言
        keywords_language = "zh" if language in ["zh", "chinese"] else "en"
        
        print(f"🔄 正在提取关键词...")
        print(f"📋 语言: {keywords_language}")
        print(f"📏 原文长度: {len(text)} 字符")
        
        # 执行关键词提取
        result = corrector.extract_keywords(text, language=keywords_language)
        
        print(f"📊 关键词提取完成:")
        print(f"  ⏱️ 处理时间: {result.processing_time:.2f}秒")
        print(f"  🎯 使用模型: {result.model_used}")
        if result.tokens_used:
            print(f"  🔢 使用Tokens: {result.tokens_used}")
        print(f"  🔍 提取到 {len(result.keywords)} 个关键词")
        
        # 保存关键词
        keywords_path = output_dir / f"{base_name}_keywords.txt"
        with open(keywords_path, 'w', encoding='utf-8') as f:
            f.write(', '.join(result.keywords))
        
        print(f"📄 关键词文件: {keywords_path}")
        
        # 显示关键词列表
        print(f"\n🔍 关键词列表:")
        for i, keyword in enumerate(result.keywords, 1):
            print(f"  {i}. {keyword}")
        
        return True
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 关键词提取过程出错: {e}")
        return False


def perform_document_formatting(
    content: str, 
    output_dir: Path, 
    base_name: str, 
    formats: list, 
    config: Config,
    source_info: str = ""
) -> bool:
    """执行文档格式化"""
    try:
        # 创建文档格式化器
        formatter = create_formatter()
        
        # 创建文档元数据
        metadata = DocumentMetadata(
            title=f"{base_name}文档",
            author=getattr(config.output, 'author', ''),
            source=source_info,
            language='zh'
        )
        
        print(f"📝 开始生成文档格式...")
        
        # 批量生成多种格式
        results = formatter.batch_format(
            content=content,
            output_dir=output_dir,
            base_name=base_name,
            formats=formats,
            metadata=metadata
        )
        
        if results:
            print(f"✅ 成功生成 {len(results)} 种格式的文档:")
            for result in results:
                print(f"  📄 {result.format.upper()}: {result.file_path} ({result.size_bytes} 字节)")
            return True
        else:
            print("❌ 未生成任何文档")
            return False
            
    except DocumentFormatterError as e:
        print(f"❌ 文档格式化失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 文档格式化过程出错: {e}")
        return False


def cmd_batch(args):
    """批量处理多个URL"""
    print(f"📦 开始批量处理: {args.input_file}")
    
    try:
        # 读取URL列表
        if not os.path.exists(args.input_file):
            print(f"❌ 输入文件不存在: {args.input_file}")
            return False
        
        with open(args.input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not urls:
            print("❌ 未找到有效的URL")
            return False
        
        print(f"📋 发现 {len(urls)} 个URL")
        
        # 加载配置
        config = load_config(args.config)
        if args.output_dir:
            config.download.output_dir = args.output_dir
        if args.cookie_browser:
            config.download.cookies.from_browser = args.cookie_browser
        if args.cookie_file:
            config.download.cookies.cookie_file = args.cookie_file
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 创建下载器
        downloader = create_downloader()
        downloader.config = config
        
        # 确定并行处理的工作线程数
        max_workers = args.max_workers
        use_parallel = not args.sequential
        progress_callback = None if args.no_progress else batch_progress_callback
        
        print(f"🚀 开始批量下载... (并行: {use_parallel}, 工作线程: {max_workers})")
        
        # 批量下载
        if use_parallel:
            results = downloader.download_batch(urls, progress_callback, max_workers)
        else:
            results = downloader.download_batch_sequential(urls, progress_callback)
        
        print()  # 换行
        
        # 统计结果
        success_count = sum(1 for result in results if result.success)
        print(f"\n📊 批量下载完成:")
        print(f"✅ 成功: {success_count}/{len(urls)}")
        print(f"❌ 失败: {len(urls) - success_count}/{len(urls)}")
        
        # 显示下载统计信息
        if success_count > 0:
            total_size = sum(result.file_size or 0 for result in results if result.success and result.file_size)
            total_duration = sum(result.duration or 0 for result in results if result.success and result.duration)
            total_time = sum(result.download_time or 0 for result in results if result.download_time)
            
            print(f"📈 下载统计:")
            print(f"  总文件大小: {total_size / (1024*1024):.1f} MB")
            print(f"  总音频时长: {total_duration / 60:.1f} 分钟")
            print(f"  总下载时间: {total_time / 60:.1f} 分钟")
            if total_time > 0:
                print(f"  平均下载速度: {(total_size / (1024*1024)) / (total_time / 60):.1f} MB/分钟")
        
        # 批量转录处理
        if args.transcribe and success_count > 0:
            print(f"\n🎙️ 开始批量转录...")
            transcribe_success_count = 0
            
            for result in results:
                if result.success and result.file_path:
                    print(f"\n🔄 转录: {Path(result.file_path).name}")
                    if perform_transcription(result.file_path, config, args):
                        transcribe_success_count += 1
                    else:
                        print(f"❌ 转录失败: {Path(result.file_path).name}")
            
            print(f"\n📊 批量转录完成:")
            print(f"✅ 转录成功: {transcribe_success_count}/{success_count}")
            print(f"❌ 转录失败: {success_count - transcribe_success_count}/{success_count}")
        
        # 显示失败的URL
        failed_results = [result for result in results if not result.success]
        if failed_results:
            print("\n❌ 失败的URL:")
            for result in failed_results:
                print(f"  {result.url}: {result.message}")
                if "cookie" in result.message.lower() or "验证" in result.message.lower():
                    print("    💡 可能需要cookie验证")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        return False


def cmd_config(args):
    """配置管理"""
    if args.show:
        # 显示当前配置
        try:
            config = load_config(args.config_file)
            print("📋 当前配置:")
            print("=" * 50)
            
            # 隐藏敏感信息
            config_dict = config.to_dict()
            if config_dict.get('deepseek', {}).get('api_key'):
                config_dict['deepseek']['api_key'] = '***已设置***'
            
            # 显示cookie配置
            print("\n🍪 Cookie配置:")
            cookies = config_dict.get('download', {}).get('cookies', {})
            print(f"  浏览器: {cookies.get('from_browser', 'None')}")
            print(f"  Cookie文件: {cookies.get('cookie_file', 'None')}")
            print(f"  自动验证: {cookies.get('auto_captcha', False)}")
            
            print(f"\n📥 下载配置:")
            download = config_dict.get('download', {})
            print(f"  输出目录: {download.get('output_dir', './temp')}")
            print(f"  音频质量: {download.get('audio_quality', 'best')}")
            print(f"  支持格式: {', '.join(download.get('supported_formats', []))}")
            
            # 网络配置
            network = download.get('network', {})
            print(f"  超时时间: {network.get('timeout', 30)}秒")
            print(f"  重试次数: {network.get('retries', 3)}")
            
            print(f"\n🔄 转录配置:")
            transcription = config_dict.get('transcription', {})
            print(f"  模型大小: {transcription.get('model_size', 'medium')}")
            print(f"  语言: {transcription.get('language', 'auto')}")
            
            print(f"\n🤖 AI配置:")
            deepseek = config_dict.get('deepseek', {})
            print(f"  API密钥: {deepseek.get('api_key', '未设置')}")
            print(f"  模型: {deepseek.get('model', 'deepseek-chat')}")
            
            # 验证配置
            is_valid, msg = config.validate()
            if is_valid:
                print(f"\n✅ 配置验证: {msg}")
            else:
                print(f"\n❌ 配置问题: {msg}")
            
        except Exception as e:
            print(f"❌ 显示配置失败: {e}")
            return False
    
    elif args.init:
        # 初始化配置文件
        config_path = Path(args.config_file or "./config/config.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建示例配置
        example_config = {
            'deepseek': {
                'api_key': 'your_deepseek_api_key_here',
                'base_url': 'https://api.deepseek.com',
                'model': 'deepseek-chat'
            },
            'download': {
                'output_dir': './temp',
                'audio_quality': 'best',
                'supported_formats': ['mp3', 'wav', 'm4a'],
                'cookies': {
                    'from_browser': 'chrome',
                    'cookie_file': None,
                    'auto_captcha': True
                },
                'network': {
                    'timeout': 30,
                    'retries': 3,
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            },
            'transcription': {
                'model_size': 'medium',
                'language': 'auto',
                'temperature': 0.0,
                'beam_size': 5
            },
            'output': {
                'default_format': 'markdown',
                'include_timestamps': True,
                'include_summary': True,
                'include_keywords': True
            },
            'logging': {
                'level': 'INFO',
                'file': './logs/video_draft_creator.log'
            }
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(example_config, f, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ 配置文件已创建: {config_path}")
        print("💡 请编辑配置文件并设置您的API密钥")
    
    elif args.test:
        # 测试配置
        try:
            config = load_config(args.config_file)
            is_valid, msg = config.validate()
            
            if is_valid:
                print(f"✅ 配置测试通过: {msg}")
                
                # 测试cookie配置
                print("🍪 测试Cookie配置...")
                cookies = config.download.cookies
                if cookies.from_browser:
                    print(f"  ✅ 浏览器cookie: {cookies.from_browser}")
                elif cookies.cookie_file:
                    if os.path.exists(cookies.cookie_file):
                        print(f"  ✅ Cookie文件: {cookies.cookie_file}")
                    else:
                        print(f"  ❌ Cookie文件不存在: {cookies.cookie_file}")
                else:
                    print("  ⚠️ 未配置cookie，可能影响某些平台的下载")
                
                return True
            else:
                print(f"❌ 配置测试失败: {msg}")
                return False
                
        except Exception as e:
            print(f"❌ 配置测试失败: {e}")
            return False
    
    return True


def cmd_correct(args):
    """纠错文本文件"""
    print(f"🤖 开始纠错文本文件: {args.text_file}")
    
    try:
        # 检查文件是否存在
        text_path = Path(args.text_file)
        if not text_path.exists():
            print(f"❌ 文本文件不存在: {args.text_file}")
            return False
        
        # 读取文本内容
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read().strip()
        
        if not text_content:
            print("❌ 文本文件为空")
            return False
        
        print(f"📏 原文长度: {len(text_content)} 字符")
        
        # 加载配置
        config = load_config(args.config)
        
        # 设置输出目录
        output_dir = text_path.parent
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # 确定语言
        if args.language == 'auto':
            # 简单的语言检测
            chinese_chars = len([c for c in text_content if '\u4e00' <= c <= '\u9fff'])
            total_chars = len([c for c in text_content if c.isalpha()])
            if total_chars > 0 and chinese_chars / total_chars > 0.3:
                language = 'zh'
            else:
                language = 'en'
            print(f"🌍 自动检测语言: {language}")
        else:
            language = args.language
        
        # 执行纠错
        base_name = text_path.stem
        success = perform_correction(text_content, output_dir, base_name, config, language)
        
        return success
        
    except Exception as e:
        print(f"❌ 文本纠错失败: {e}")
        return False


def cmd_format(args):
    """格式化文本文件为文档"""
    print(f"📝 开始格式化文本文件: {args.text_file}")
    
    try:
        # 检查文件是否存在
        text_path = Path(args.text_file)
        if not text_path.exists():
            print(f"❌ 文本文件不存在: {args.text_file}")
            return False
        
        # 读取文本内容
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read().strip()
        
        if not text_content:
            print("❌ 文本文件为空")
            return False
        
        print(f"📏 文本长度: {len(text_content)} 字符")
        
        # 加载配置
        config = load_config(args.config)
        
        # 设置输出目录
        output_dir = Path(args.output_dir) if args.output_dir else text_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建文档格式化器
        formatter = create_formatter()
        
        # 创建文档元数据
        metadata = DocumentMetadata(
            title=args.title or f"{text_path.stem}文档",
            author=args.author or getattr(config.output, 'author', ''),
            source=args.source or f"文本文件: {text_path.name}",
            language='zh'
        )
        
        print(f"📋 文档信息:")
        print(f"  标题: {metadata.title}")
        print(f"  作者: {metadata.author}")
        print(f"  来源: {metadata.source}")
        
        # 批量生成多种格式
        base_name = text_path.stem
        results = formatter.batch_format(
            content=text_content,
            output_dir=output_dir,
            base_name=base_name,
            formats=args.formats,
            metadata=metadata
        )
        
        if results:
            print(f"\n✅ 成功生成 {len(results)} 种格式的文档:")
            for result in results:
                print(f"  📄 {result.format.upper()}: {result.file_path} ({result.size_bytes} 字节)")
            
            # 显示文本预览
            preview_length = 200
            if len(text_content) > preview_length:
                preview = text_content[:preview_length] + "..."
            else:
                preview = text_content
            
            print(f"\n📝 内容预览:")
            print(f"「{preview}」")
            
            return True
        else:
            print("❌ 未生成任何文档")
            return False
            
    except DocumentFormatterError as e:
        print(f"❌ 文档格式化失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 格式化过程出错: {e}")
        return False


def cmd_summarize(args):
    """生成文本摘要"""
    print(f"📝 开始生成摘要: {args.text_file}")
    
    try:
        # 检查文件
        text_file = Path(args.text_file)
        if not text_file.exists():
            print(f"❌ 文件不存在: {args.text_file}")
            return False
        
        # 读取文本
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ 文件内容为空")
            return False
        
        # 加载配置
        config = load_config(args.config)
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 检测语言
        language = args.language
        if language == 'auto':
            # 简单的语言检测
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text)
            language = 'zh' if chinese_chars / total_chars > 0.3 else 'en'
            print(f"🌍 检测到语言: {language}")
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.correction)
        
        # 生成摘要
        print("🔄 正在生成摘要...")
        result = corrector.summarize_text(text, language)
        
        # 设置输出目录
        output_dir = Path(args.output_dir) if args.output_dir else text_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存摘要
        base_name = text_file.stem
        summary_file = output_dir / f"{base_name}_summary.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(result.summary)
        
        print(f"✅ 摘要生成完成")
        print(f"📄 摘要文件: {summary_file}")
        print(f"⏱️ 处理时间: {result.processing_time:.2f}秒")
        if result.tokens_used:
            print(f"🎯 使用tokens: {result.tokens_used}")
        
        # 显示摘要预览
        preview_length = 200
        preview = result.summary[:preview_length] + "..." if len(result.summary) > preview_length else result.summary
        print(f"\n📝 摘要预览:")
        print(f"「{preview}」")
        
        return True
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 摘要生成失败: {e}")
        return False


def cmd_keywords(args):
    """提取关键词"""
    print(f"🔍 开始提取关键词: {args.text_file}")
    
    try:
        # 检查文件
        text_file = Path(args.text_file)
        if not text_file.exists():
            print(f"❌ 文件不存在: {args.text_file}")
            return False
        
        # 读取文本
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ 文件内容为空")
            return False
        
        # 加载配置
        config = load_config(args.config)
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 检测语言
        language = args.language
        if language == 'auto':
            # 简单的语言检测
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text)
            language = 'zh' if chinese_chars / total_chars > 0.3 else 'en'
            print(f"🌍 检测到语言: {language}")
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.correction)
        
        # 提取关键词
        print("🔄 正在提取关键词...")
        result = corrector.extract_keywords(text, language)
        
        # 设置输出目录
        output_dir = Path(args.output_dir) if args.output_dir else text_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存关键词
        base_name = text_file.stem
        keywords_file = output_dir / f"{base_name}_keywords.txt"
        
        with open(keywords_file, 'w', encoding='utf-8') as f:
            f.write(', '.join(result.keywords))
        
        print(f"✅ 关键词提取完成")
        print(f"📄 关键词文件: {keywords_file}")
        print(f"⏱️ 处理时间: {result.processing_time:.2f}秒")
        if result.tokens_used:
            print(f"🎯 使用tokens: {result.tokens_used}")
        print(f"🔢 提取到 {len(result.keywords)} 个关键词")
        
        # 显示关键词
        print(f"\n🔍 关键词列表:")
        for i, keyword in enumerate(result.keywords, 1):
            print(f"  {i}. {keyword}")
        
        return True
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 关键词提取失败: {e}")
        return False


def cmd_analyze(args):
    """综合文本分析"""
    print(f"🔬 开始综合文本分析: {args.text_file}")
    
    try:
        # 检查文件
        text_file = Path(args.text_file)
        if not text_file.exists():
            print(f"❌ 文件不存在: {args.text_file}")
            return False
        
        # 读取文本
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            print("❌ 文件内容为空")
            return False
        
        # 加载配置
        config = load_config(args.config)
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 检测语言
        language = args.language
        if language == 'auto':
            # 简单的语言检测
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text)
            language = 'zh' if chinese_chars / total_chars > 0.3 else 'en'
            print(f"🌍 检测到语言: {language}")
        
        # 创建纠错器
        corrector = create_corrector_from_config(config.correction)
        
        # 执行综合分析
        print("🔄 正在执行综合分析...")
        result = corrector.analyze_text(
            text, 
            language,
            include_correction=not args.no_correction,
            include_summary=not args.no_summary,
            include_keywords=not args.no_keywords
        )
        
        # 设置输出目录
        output_dir = Path(args.output_dir) if args.output_dir else text_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        base_name = text_file.stem
        
        # 保存结果
        if result.corrected_text:
            corrected_file = output_dir / f"{base_name}_corrected.txt"
            with open(corrected_file, 'w', encoding='utf-8') as f:
                f.write(result.corrected_text)
            print(f"📄 纠错文本: {corrected_file}")
        
        if result.summary:
            summary_file = output_dir / f"{base_name}_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(result.summary)
            print(f"📄 摘要文件: {summary_file}")
        
        if result.keywords:
            keywords_file = output_dir / f"{base_name}_keywords.txt"
            with open(keywords_file, 'w', encoding='utf-8') as f:
                f.write(', '.join(result.keywords))
            print(f"📄 关键词文件: {keywords_file}")
        
        # 生成综合报告
        report_file = output_dir / f"{base_name}_analysis_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("文本分析报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"原文件: {text_file.name}\n")
            f.write(f"分析时间: {result.total_processing_time:.2f}秒\n")
            if result.total_tokens_used:
                f.write(f"总tokens: {result.total_tokens_used}\n")
            f.write(f"语言: {language}\n\n")
            
            if result.corrected_text:
                f.write("纠错文本:\n")
                f.write("-" * 20 + "\n")
                f.write(result.corrected_text + "\n\n")
            
            if result.summary:
                f.write("文本摘要:\n")
                f.write("-" * 20 + "\n")
                f.write(result.summary + "\n\n")
            
            if result.keywords:
                f.write("关键词:\n")
                f.write("-" * 20 + "\n")
                f.write(', '.join(result.keywords) + "\n\n")
        
        print(f"✅ 综合分析完成")
        print(f"📄 分析报告: {report_file}")
        print(f"⏱️ 总处理时间: {result.total_processing_time:.2f}秒")
        if result.total_tokens_used:
            print(f"🎯 总tokens: {result.total_tokens_used}")
        
        # 显示摘要信息
        if result.summary:
            preview_length = 150
            preview = result.summary[:preview_length] + "..." if len(result.summary) > preview_length else result.summary
            print(f"\n📝 摘要预览:")
            print(f"「{preview}」")
        
        if result.keywords:
            print(f"\n🔍 关键词 ({len(result.keywords)}个):")
            print(f"「{', '.join(result.keywords[:10])}{'...' if len(result.keywords) > 10 else ''}」")
        
        return True
        
    except DeepSeekAPIError as e:
        print(f"❌ API调用失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 综合分析失败: {e}")
        return False


def cmd_test(args):
    """测试功能"""
    print("🧪 运行测试...")
    
    # 测试URL列表
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # 经典测试视频
        "https://www.bilibili.com/video/BV1GJ411x7h7"   # B站测试视频
    ]
    
    try:
        config = load_config(args.config)
        if args.cookie_browser:
            config.download.cookies.from_browser = args.cookie_browser
        if args.cookie_file:
            config.download.cookies.cookie_file = args.cookie_file
        
        downloader = create_downloader()
        downloader.config = config
        
        print("🔍 测试URL支持检查...")
        for url in test_urls:
            supported, platform = downloader.check_url_support(url)
            status = "✅" if supported else "❌"
            print(f"  {status} {url} - {platform}")
        
        print("\n📋 测试视频信息获取...")
        test_url = test_urls[0]  # YouTube测试
        info = downloader.get_video_info(test_url)
        
        if info:
            print(f"  ✅ 成功获取信息:")
            print(f"    标题: {info['title'][:50]}...")
            print(f"    平台: {info['platform']}")
            print(f"    时长: {info['duration']}秒")
        else:
            print(f"  ❌ 无法获取视频信息")
            print(f"  💡 可能需要cookie验证")
        
        print("\n✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def cmd_transcribe(args):
    """转录音频文件"""
    print(f"🎙️ 开始转录: {args.audio_file}")
    
    try:
        # 检查音频文件
        audio_path = Path(args.audio_file)
        if not audio_path.exists():
            print(f"❌ 音频文件不存在: {args.audio_file}")
            return False
        
        # 加载配置
        config = load_config(args.config)
        
        # 从命令行参数覆盖配置
        if args.model_size:
            config.transcription.model_size = args.model_size
        if args.language:
            config.transcription.language = args.language
        
        # 设置输出目录
        if args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        else:
            output_dir = audio_path.parent
        
        # 设置日志
        setup_logging(config.logging.level, config.logging.file)
        
        # 创建转录器
        transcriber = create_transcriber(
            model_size=config.transcription.model_size,
            device="auto",
            compute_type="auto"
        )
        
        # 设置语言
        language = config.transcription.language if config.transcription.language != 'auto' else None
        
        print(f"🔄 正在转录: {audio_path.name}")
        print(f"📋 模型: {config.transcription.model_size}")
        print(f"🌍 语言: {language or '自动检测'}")
        print(f"📁 输出目录: {output_dir}")
        
        # 进度回调
        def transcription_progress(segment_count, segment):
            print(f"\r🎙️ 已处理: {segment_count} 段", end='', flush=True)
        
        # 执行转录
        result = transcriber.transcribe_audio(
            audio_path,
            language=language,
            beam_size=config.transcription.beam_size,
            temperature=config.transcription.temperature,
            progress_callback=transcription_progress
        )
        
        print(f"\n📊 转录完成:")
        print(f"  🌍 检测语言: {result.language} ({result.language_probability:.2f})")
        print(f"  ⏱️ 音频时长: {result.duration:.2f}秒")
        print(f"  📝 文本段数: {len(result.segments)}")
        
        # 生成输出文件
        base_name = audio_path.stem
        output_format = args.format
        
        if output_format in ['srt', 'all']:
            srt_path = output_dir / f"{base_name}.srt"
            transcriber.generate_srt(result, srt_path)
            print(f"📄 SRT字幕: {srt_path}")
        
        if output_format in ['vtt', 'all']:
            vtt_path = output_dir / f"{base_name}.vtt"
            transcriber.generate_vtt(result, vtt_path)
            print(f"📄 VTT字幕: {vtt_path}")
        
        if output_format in ['txt', 'all']:
            txt_path = output_dir / f"{base_name}_transcript.txt"
            transcriber.generate_text(result, txt_path)
            print(f"📄 转录文本: {txt_path}")
        
        # 显示文本预览
        preview_length = 200
        if len(result.text) > preview_length:
            preview = result.text[:preview_length] + "..."
        else:
            preview = result.text
        
        print(f"\n📝 文本预览:")
        print(f"「{preview}」")
        
        return True
        
    except TranscriptionError as e:
        print(f"❌ 转录失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 转录过程出错: {e}")
        return False


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="视频草稿创建工具 - 下载、转录、AI处理视频内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本下载
  %(prog)s process https://www.youtube.com/watch?v=VIDEO_ID

  # 使用Chrome浏览器cookie下载
  %(prog)s process https://www.youtube.com/watch?v=VIDEO_ID --cookie-browser chrome

  # 使用cookie文件下载
  %(prog)s process https://www.youtube.com/watch?v=VIDEO_ID --cookie-file cookies.txt

  # 批量下载
  %(prog)s batch urls.txt --cookie-browser firefox

  # 转录音频文件
  %(prog)s transcribe audio.mp3 --model-size medium --language zh

  # 查看配置
  %(prog)s config --show

  # 初始化配置文件
  %(prog)s config --init
        """
    )
    
    # 全局参数
    parser.add_argument('--config', '-c', 
                       help='配置文件路径 (默认: ./config/config.yaml)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细日志')
    
    # Cookie相关全局参数
    parser.add_argument('--cookie-browser', 
                       choices=['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave'],
                       help='从浏览器导入cookie')
    parser.add_argument('--cookie-file',
                       help='Cookie文件路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # process 命令
    parser_process = subparsers.add_parser('process', help='处理单个视频URL')
    parser_process.add_argument('url', help='视频URL')
    parser_process.add_argument('--output-dir', '-o', 
                              help='输出目录 (覆盖配置文件设置)')
    parser_process.add_argument('--output-name', '-n',
                              help='输出文件名(不含扩展名)')
    parser_process.add_argument('--audio-quality', '-q',
                              choices=['best', 'worst', '128', '192', '256', '320'],
                              help='音频质量')
    parser_process.add_argument('--transcribe', '-t', action='store_true',
                              help='下载后进行转录')
    parser_process.add_argument('--correct', action='store_true',
                              help='转录后进行AI文本纠错 (需要--transcribe)')
    parser_process.add_argument('--summarize', action='store_true',
                              help='生成文本摘要 (需要--transcribe)')
    parser_process.add_argument('--keywords', action='store_true',
                              help='提取关键词 (需要--transcribe)')
    parser_process.add_argument('--info-only', action='store_true',
                              help='仅获取视频信息，不下载')
    parser_process.add_argument('--format', '-f',
                              choices=['markdown', 'txt', 'docx'],
                              help='输出文档格式')
    parser_process.add_argument('--profile', '-p',
                              help='使用指定的配置预设')
    parser_process.add_argument('--verbose', '-v', action='store_true',
                              help='详细输出模式')
    
    # batch 命令
    parser_batch = subparsers.add_parser('batch', help='批量处理多个URL')
    parser_batch.add_argument('input_file', help='包含URL的文本文件')
    parser_batch.add_argument('--output-dir', '-o',
                            help='输出目录')
    parser_batch.add_argument('--transcribe', '-t', action='store_true',
                            help='下载后进行转录')
    parser_batch.add_argument('--correct', action='store_true',
                            help='转录后进行AI文本纠错 (需要--transcribe)')
    parser_batch.add_argument('--summarize', action='store_true',
                            help='生成文本摘要 (需要--transcribe)')
    parser_batch.add_argument('--keywords', action='store_true',
                            help='提取关键词 (需要--transcribe)')
    parser_batch.add_argument('--format', '-f',
                            choices=['markdown', 'txt', 'docx'],
                            help='输出文档格式')
    parser_batch.add_argument('--max-workers', '-w', type=int, default=3,
                            help='最大并行工作线程数 (默认: 3)')
    parser_batch.add_argument('--sequential', action='store_true',
                            help='使用顺序处理而非并行处理')
    parser_batch.add_argument('--no-progress', action='store_true',
                            help='禁用进度显示')
    parser_batch.add_argument('--profile', '-p',
                            help='使用指定的配置预设')
    parser_batch.add_argument('--verbose', '-v', action='store_true',
                            help='详细输出模式')
    
    # config 命令
    parser_config = subparsers.add_parser('config', help='配置管理')
    config_group = parser_config.add_mutually_exclusive_group(required=True)
    config_group.add_argument('--show', action='store_true',
                            help='显示当前配置')
    config_group.add_argument('--init', action='store_true',
                            help='初始化配置文件')
    config_group.add_argument('--test', action='store_true',
                            help='测试配置')
    config_group.add_argument('--list-profiles', action='store_true',
                            help='列出所有配置预设')
    config_group.add_argument('--save-profile',
                            help='保存当前配置为预设')
    config_group.add_argument('--show-profile',
                            help='显示指定配置预设的详情')
    config_group.add_argument('--delete-profile',
                            help='删除指定的配置预设')
    parser_config.add_argument('--config-file',
                             help='配置文件路径')
    parser_config.add_argument('--description',
                             help='配置预设的描述信息 (与--save-profile一起使用)')
    
    # transcribe 命令
    parser_transcribe = subparsers.add_parser('transcribe', help='转录音频文件')
    parser_transcribe.add_argument('audio_file', help='音频文件路径')
    parser_transcribe.add_argument('--output-dir', '-o',
                                 help='输出目录')
    parser_transcribe.add_argument('--model-size', '-m',
                                 choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
                                 help='转录模型大小')
    parser_transcribe.add_argument('--language', '-l',
                                 help='音频语言 (如: zh, en, auto)')
    parser_transcribe.add_argument('--format', '-f',
                                 choices=['srt', 'vtt', 'txt', 'all'],
                                 default='all',
                                 help='输出格式')
    
    # correct 命令
    parser_correct = subparsers.add_parser('correct', help='纠错文本文件')
    parser_correct.add_argument('text_file', help='文本文件路径')
    parser_correct.add_argument('--output-dir', '-o',
                               help='输出目录')
    parser_correct.add_argument('--language', '-l',
                               choices=['zh', 'en', 'auto'],
                               default='auto',
                               help='文本语言')
    
    # format 命令
    parser_format = subparsers.add_parser('format', help='格式化文本文件为文档')
    parser_format.add_argument('text_file', help='文本文件路径')
    parser_format.add_argument('--output-dir', '-o',
                              help='输出目录')
    parser_format.add_argument('--formats', '-f',
                              nargs='+',
                              choices=['markdown', 'txt', 'docx'],
                              default=['markdown'],
                              help='输出格式 (可多选)')
    parser_format.add_argument('--title', '-t',
                              help='文档标题')
    parser_format.add_argument('--author', '-a',
                              help='文档作者')
    parser_format.add_argument('--source', '-s',
                              help='文档来源信息')
    
    # summarize 命令
    parser_summarize = subparsers.add_parser('summarize', help='生成文本摘要')
    parser_summarize.add_argument('text_file', help='文本文件路径')
    parser_summarize.add_argument('--output-dir', '-o',
                                 help='输出目录')
    parser_summarize.add_argument('--language', '-l',
                                 choices=['zh', 'en', 'auto'],
                                 default='auto',
                                 help='文本语言')
    
    # keywords 命令
    parser_keywords = subparsers.add_parser('keywords', help='提取关键词')
    parser_keywords.add_argument('text_file', help='文本文件路径')
    parser_keywords.add_argument('--output-dir', '-o',
                                help='输出目录')
    parser_keywords.add_argument('--language', '-l',
                                choices=['zh', 'en', 'auto'],
                                default='auto',
                                help='文本语言')
    
    # analyze 命令 (综合分析)
    parser_analyze = subparsers.add_parser('analyze', help='综合文本分析(纠错+摘要+关键词)')
    parser_analyze.add_argument('text_file', help='文本文件路径')
    parser_analyze.add_argument('--output-dir', '-o',
                               help='输出目录')
    parser_analyze.add_argument('--language', '-l',
                               choices=['zh', 'en', 'auto'],
                               default='auto',
                               help='文本语言')
    parser_analyze.add_argument('--no-correction', action='store_true',
                               help='跳过文本纠错')
    parser_analyze.add_argument('--no-summary', action='store_true',
                               help='跳过摘要生成')
    parser_analyze.add_argument('--no-keywords', action='store_true',
                               help='跳过关键词提取')
    
    # test 命令
    parser_test = subparsers.add_parser('test', help='运行测试')
    
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 根据命令执行相应函数
    try:
        if args.command == 'process':
            success = cmd_process(args)
        elif args.command == 'batch':
            success = cmd_batch(args)
        elif args.command == 'config':
            success = cmd_config(args)
        elif args.command == 'transcribe':
            success = cmd_transcribe(args)
        elif args.command == 'correct':
            success = cmd_correct(args)
        elif args.command == 'format':
            success = cmd_format(args)
        elif args.command == 'summarize':
            success = cmd_summarize(args)
        elif args.command == 'keywords':
            success = cmd_keywords(args)
        elif args.command == 'analyze':
            success = cmd_analyze(args)
        elif args.command == 'test':
            success = cmd_test(args)
        else:
            print(f"❌ 未知命令: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        return 1
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main()) 