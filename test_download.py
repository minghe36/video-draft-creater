#!/usr/bin/env python3
"""
下载器测试脚本
测试音频下载功能和Cookie配置
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from video_draft_creator.downloader import create_downloader
from video_draft_creator.config import load_config, Config


def test_cookie_config():
    """测试Cookie配置"""
    print("🍪 测试Cookie配置...")
    
    # 加载配置
    config = load_config()
    cookies = config.download.cookies
    
    print(f"  浏览器Cookie: {cookies.from_browser}")
    print(f"  Cookie文件: {cookies.cookie_file}")
    print(f"  自动验证: {cookies.auto_captcha}")
    
    # 测试浏览器Cookie
    if cookies.from_browser:
        print(f"  ✅ 配置从 {cookies.from_browser} 浏览器导入Cookie")
    elif cookies.cookie_file:
        if os.path.exists(cookies.cookie_file):
            print(f"  ✅ Cookie文件存在: {cookies.cookie_file}")
        else:
            print(f"  ❌ Cookie文件不存在: {cookies.cookie_file}")
    else:
        print("  ⚠️ 未配置Cookie，可能影响下载")
    
    return True


def test_url_support():
    """测试URL支持"""
    print("🔍 测试URL支持...")
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # YouTube
        "https://www.bilibili.com/video/BV1GJ411x7h7",  # Bilibili
        "https://v.qq.com/x/cover/test",                # 腾讯视频  
        "https://weibo.com/tv/show/test",               # 微博视频
        "https://invalid-site.com/video"               # 不支持的网站
    ]
    
    downloader = create_downloader()
    
    for url in test_urls:
        supported, platform = downloader.check_url_support(url)
        status = "✅" if supported else "❌"
        print(f"  {status} {url} - {platform}")
    
    return True


def test_video_info():
    """测试视频信息获取"""
    print("📋 测试视频信息获取...")
    
    # 使用一个公开的测试视频
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    downloader = create_downloader()
    
    print(f"  测试URL: {test_url}")
    
    info = downloader.get_video_info(test_url)
    
    if info:
        print(f"  ✅ 成功获取视频信息:")
        print(f"    标题: {info['title'][:50]}...")
        print(f"    时长: {info['duration']}秒")
        print(f"    平台: {info['platform']}")
        print(f"    上传者: {info['uploader']}")
        return True
    else:
        print(f"  ❌ 无法获取视频信息")
        print(f"  💡 可能需要Cookie验证，尝试运行:")
        print(f"     python test_download.py --with-cookies")
        return False


def test_download_with_cookies():
    """测试带Cookie的下载"""
    print("🎵 测试带Cookie的音频下载...")
    
    # 修改配置使用Chrome浏览器Cookie
    config = load_config()
    config.download.cookies.from_browser = "chrome"
    config.download.output_dir = "./temp_test"
    
    downloader = create_downloader()
    downloader.config = config
    
    # 使用一个短视频进行测试
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"  测试URL: {test_url}")
    print(f"  输出目录: {config.download.output_dir}")
    print(f"  Cookie来源: Chrome浏览器")
    
    def progress_callback(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            print(f"\r    下载进度: {percent}", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\n    ✅ 下载完成")
        elif d['status'] == 'error':
            print(f"\n    ❌ 下载失败")
    
    success, message, file_path = downloader.download_audio(
        test_url, 
        "test_download",
        progress_callback
    )
    
    if success:
        print(f"  ✅ {message}")
        if file_path:
            print(f"  📁 文件路径: {file_path}")
            
            # 检查文件是否存在且不为空
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) 
                print(f"  📊 文件大小: {file_size / 1024 / 1024:.1f} MB")
                
                # 清理测试文件
                try:
                    os.remove(file_path)
                    print(f"  🧹 已清理测试文件")
                except:
                    pass
            else:
                print(f"  ❌ 文件不存在: {file_path}")
                return False
    else:
        print(f"  ❌ {message}")
        if "cookie" in message.lower():
            print(f"  💡 提示: 请确保Chrome浏览器中已登录YouTube")
        return False
    
    return success


def test_cli_commands():
    """测试CLI命令"""
    print("⚙️ 测试CLI命令...")
    
    import subprocess
    
    # 测试帮助命令
    try:
        result = subprocess.run([
            sys.executable, "-m", "video_draft_creator.cli", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ CLI帮助命令正常")
        else:
            print("  ❌ CLI帮助命令失败")
            return False
    except Exception as e:
        print(f"  ❌ CLI命令测试失败: {e}")
        return False
    
    # 测试配置显示命令
    try:
        result = subprocess.run([
            sys.executable, "-m", "video_draft_creator.cli", 
            "config", "--show"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("  ✅ 配置显示命令正常")
        else:
            print("  ❌ 配置显示命令失败")
            print(f"    错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ 配置命令测试失败: {e}")
        return False
    
    return True


def main():
    """主测试函数"""
    print("🧪 Video Draft Creator 下载器测试")
    print("=" * 50)
    
    # 检查命令行参数
    with_cookies = "--with-cookies" in sys.argv
    
    tests = [
        ("Cookie配置", test_cookie_config),
        ("URL支持", test_url_support),
        ("视频信息", test_video_info),
        ("CLI命令", test_cli_commands),
    ]
    
    # 如果指定了cookie测试，添加下载测试
    if with_cookies:
        tests.append(("Cookie下载", test_download_with_cookies))
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n📋 {name}测试...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {name}测试通过")
            else:
                print(f"❌ {name}测试失败")
        except Exception as e:
            print(f"❌ {name}测试异常: {e}")
    
    # 总结
    print(f"\n📊 测试总结:")
    print(f"  总数: {total}")
    print(f"  通过: {passed}")
    print(f"  失败: {total - passed}")
    
    if passed == total:
        print("🎉 所有测试通过！")
        
        if not with_cookies:
            print("\n💡 提示:")
            print("  运行 'python test_download.py --with-cookies' 测试实际下载功能")
            print("  确保Chrome浏览器中已登录YouTube账号")
    else:
        print("⚠️ 部分测试失败，请检查配置")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 