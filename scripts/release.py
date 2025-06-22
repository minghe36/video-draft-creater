#!/usr/bin/env python3
"""
Video Draft Creator 发布脚本
自动化PyPI发布流程
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, check=True):
    """执行命令并返回结果"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stderr:
            print(f"错误信息: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def check_prerequisites():
    """检查发布前置条件"""
    print("检查发布前置条件...")
    
    # 检查是否在git仓库中
    result = run_command("git status", check=False)
    if result.returncode != 0:
        print("错误: 当前目录不是git仓库")
        return False
    
    # 检查工作目录是否干净
    result = run_command("git status --porcelain", check=False)
    if result.stdout.strip():
        print("警告: 工作目录有未提交的变更")
        response = input("是否继续? (y/N): ")
        if response.lower() != 'y':
            return False
    
    # 检查必要的包是否安装
    required_packages = ['build', 'twine']
    for package in required_packages:
        result = run_command(f"python -m pip show {package}", check=False)
        if result.returncode != 0:
            print(f"安装缺失的包: {package}")
            run_command(f"python -m pip install {package}")
    
    return True

def run_tests():
    """运行测试套件"""
    print("运行测试套件...")
    result = run_command("python -m pytest tests/ -v", check=False)
    if result.returncode != 0:
        print("测试失败，无法继续发布")
        return False
    return True

def build_package():
    """构建分发包"""
    print("清理旧的构建文件...")
    run_command("rm -rf build/ dist/ *.egg-info/")
    
    print("构建分发包...")
    run_command("python -m build")
    
    # 检查构建的包
    print("检查构建的包...")
    run_command("python -m twine check dist/*")
    
    return True

def upload_to_testpypi():
    """上传到TestPyPI"""
    print("上传到TestPyPI...")
    run_command("python -m twine upload --repository testpypi dist/*")

def upload_to_pypi():
    """上传到PyPI"""
    print("上传到PyPI...")
    run_command("python -m twine upload dist/*")

def create_git_tag(version):
    """创建git标签"""
    print(f"创建git标签 v{version}...")
    run_command(f"git tag v{version}")
    run_command("git push origin --tags")

def main():
    parser = argparse.ArgumentParser(description="Video Draft Creator 发布脚本")
    parser.add_argument("--version", required=True, help="发布版本号")
    parser.add_argument("--test", action="store_true", help="发布到TestPyPI")
    parser.add_argument("--skip-tests", action="store_true", help="跳过测试")
    parser.add_argument("--skip-tag", action="store_true", help="跳过创建git标签")
    
    args = parser.parse_args()
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"开始发布 Video Draft Creator v{args.version}")
    print(f"项目目录: {project_root}")
    
    # 检查前置条件
    if not check_prerequisites():
        print("前置条件检查失败")
        sys.exit(1)
    
    # 运行测试
    if not args.skip_tests:
        if not run_tests():
            sys.exit(1)
    else:
        print("跳过测试")
    
    # 构建包
    if not build_package():
        print("构建失败")
        sys.exit(1)
    
    # 上传包
    if args.test:
        upload_to_testpypi()
        print(f"测试发布完成！")
        print(f"测试安装命令: pip install --index-url https://test.pypi.org/simple/ video-draft-creator=={args.version}")
    else:
        # 确认发布到正式PyPI
        response = input(f"确认发布 v{args.version} 到PyPI? (y/N): ")
        if response.lower() == 'y':
            upload_to_pypi()
            
            # 创建git标签
            if not args.skip_tag:
                create_git_tag(args.version)
            
            print(f"发布完成！")
            print(f"安装命令: pip install video-draft-creator=={args.version}")
        else:
            print("发布取消")
    
    print("清理构建文件...")
    run_command("rm -rf build/ *.egg-info/")

if __name__ == "__main__":
    main() 