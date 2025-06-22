import os
from setuptools import setup, find_packages

# 获取项目根目录
here = os.path.abspath(os.path.dirname(__file__))

# 读取README文件
with open(os.path.join(here, "README.md"), "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 读取requirements.txt，过滤掉测试和文档依赖
with open(os.path.join(here, "requirements.txt"), "r", encoding="utf-8") as fh:
    lines = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    
# 分离核心依赖和可选依赖
core_requirements = []
doc_requirements = []
test_requirements = []

for line in lines:
    if any(pkg in line.lower() for pkg in ['sphinx', 'myst']):
        doc_requirements.append(line)
    elif any(pkg in line.lower() for pkg in ['pytest', 'mock', 'cov']):
        test_requirements.append(line)
    else:
        core_requirements.append(line)

# 项目版本
VERSION = "0.1.0"

setup(
    name="video-draft-creator",
    version=VERSION,
    author="Video Draft Creator Team",
    author_email="video-draft-creator@example.com",
    description="强大的视频音频下载、转录和AI纠错工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/video-draft-creator",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/video-draft-creator/issues",
        "Source": "https://github.com/yourusername/video-draft-creator",
        "Documentation": "https://video-draft-creator.readthedocs.io/",
        "Changelog": "https://github.com/yourusername/video-draft-creator/blob/main/CHANGELOG.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "video_draft_creator": [
            "templates/*.md",
            "templates/*.txt",
            "config/*.yaml",
        ],
    },
    classifiers=[
        # 开发状态
        "Development Status :: 4 - Beta",
        
        # 目标受众
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        
        # 主题分类
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Utilities",
        
        # 许可证
        "License :: OSI Approved :: MIT License",
        
        # 操作系统
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        
        # Python版本
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        
        # 自然语言
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: English",
    ],
    keywords=[
        "video", "audio", "transcription", "whisper", "deepseek",
        "download", "yt-dlp", "speech-to-text", "ai", "nlp",
        "video-processing", "subtitle", "transcript", "bilibili",
        "youtube", "命令行", "视频下载", "语音转录", "文本纠错"
    ],
    python_requires=">=3.8",
    install_requires=core_requirements,
    extras_require={
        "dev": test_requirements + doc_requirements + [
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
        "docs": doc_requirements + [
            "sphinx-autobuild>=2021.3.14",
        ],
        "test": test_requirements,
        "gpu": [
            "torch>=2.0.0",
            "torchaudio>=2.0.0",
        ],
        "all": test_requirements + doc_requirements + [
            "black>=23.0.0",
            "isort>=5.12.0", 
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "sphinx-autobuild>=2021.3.14",
            "torch>=2.0.0",
            "torchaudio>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "video-draft-creator=video_draft_creator.cli:main",
            "vdc=video_draft_creator.cli:main",  # 简短别名
        ],
    },
    zip_safe=False,
    platforms=["any"],
    
    # 元数据用于PyPI搜索和分类
    license="MIT",
    maintainer="Video Draft Creator Team",
    maintainer_email="video-draft-creator@example.com",
) 