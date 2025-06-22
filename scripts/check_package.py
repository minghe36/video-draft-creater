#!/usr/bin/env python3
"""
包验证脚本 - 在发布前验证包的完整性
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, check=True):
    """执行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        return e

def check_package_structure():
    """检查包结构"""
    print("检查包结构...")
    
    required_files = [
        "setup.py",
        "pyproject.toml", 
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "requirements.txt",
        "MANIFEST.in",
        "src/video_draft_creator/__init__.py",
        "src/video_draft_creator/cli.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"缺失的必要文件: {missing_files}")
        return False
    
    print("✓ 包结构检查通过")
    return True

def check_imports():
    """检查核心模块导入"""
    print("检查模块导入...")
    
    try:
        # 添加src目录到Python路径
        sys.path.insert(0, str(Path("src").absolute()))
        
        import video_draft_creator
        print(f"✓ 成功导入 video_draft_creator (版本: {getattr(video_draft_creator, '__version__', '未定义')})")
        
        from video_draft_creator.cli import main
        print("✓ 成功导入 CLI 主函数")
        
        from video_draft_creator.downloader import VideoDownloader
        print("✓ 成功导入 VideoDownloader")
        
        from video_draft_creator.transcriber import AudioTranscriber
        print("✓ 成功导入 AudioTranscriber")
        
        from video_draft_creator.corrector import TextCorrector
        print("✓ 成功导入 TextCorrector")
        
        from video_draft_creator.output_formatter import OutputFormatter
        print("✓ 成功导入 OutputFormatter")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    finally:
        # 移除添加的路径
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))

def check_dependencies():
    """检查依赖项"""
    print("检查依赖项...")
    
    # 读取requirements.txt
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    failed_deps = []
    for req in requirements:
        # 跳过文档和测试依赖
        if any(pkg in req.lower() for pkg in ['sphinx', 'pytest', 'mock', 'cov']):
            continue
            
        package_name = req.split(">=")[0].split("==")[0].split("<=")[0]
        result = run_command(f"python -m pip show {package_name}", check=False)
        if result.returncode != 0:
            failed_deps.append(package_name)
    
    if failed_deps:
        print(f"✗ 缺失的依赖: {failed_deps}")
        return False
    
    print("✓ 所有核心依赖都已安装")
    return True

def check_entry_points():
    """检查入口点"""
    print("检查命令行入口点...")
    
    # 检查是否能找到CLI命令
    result = run_command("python -m video_draft_creator --help", check=False)
    if result.returncode != 0:
        print("✗ CLI入口点测试失败")
        return False
    
    print("✓ CLI入口点工作正常")
    return True

def lint_code():
    """代码质量检查"""
    print("运行代码质量检查...")
    
    # 检查Python语法
    result = run_command("python -m py_compile src/video_draft_creator/*.py", check=False)
    if result.returncode != 0:
        print("✗ Python语法检查失败")
        return False
    
    print("✓ Python语法检查通过")
    return True

def main():
    """主函数"""
    print("=== Video Draft Creator 包验证 ===\n")
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    checks = [
        check_package_structure,
        check_dependencies,
        check_imports,
        check_entry_points,
        lint_code,
    ]
    
    failed_checks = []
    
    for check in checks:
        try:
            if not check():
                failed_checks.append(check.__name__)
        except Exception as e:
            print(f"✗ {check.__name__} 执行出错: {e}")
            failed_checks.append(check.__name__)
        print()
    
    if failed_checks:
        print(f"❌ 验证失败，以下检查未通过: {failed_checks}")
        sys.exit(1)
    else:
        print("✅ 所有验证通过！包可以安全发布。")

if __name__ == "__main__":
    main() 