# Video Draft Creator

一个基于 Python 的强大命令行工具，专为从流媒体视频中提取音频、进行高精度语音转录并生成经过 AI 纠错的结构化文稿而设计。

## 🎯 功能特性

- 🎥 **多平台视频音频下载**：使用 yt-dlp 支持 YouTube、B站、优酷等主流视频平台
- 🍪 **智能 Cookie 管理**：支持 6 大主流浏览器的 Cookie 自动导入
- 🎤 **高精度语音转录**：基于 faster-whisper 实现快速、准确的语音转文字
- 🤖 **AI 智能纠错**：集成 DeepSeek API 进行智能文本纠错和结构化
- 📊 **智能文本分析**：自动生成摘要、提取关键词和主题分析
- 📄 **多格式输出**：支持 Markdown、TXT、DOCX、SRT、VTT 等多种输出格式
- ⚡ **并行处理**：支持批量下载和并行转录处理
- 🔧 **灵活配置**：支持配置文件和命令行参数的灵活组合
- 📈 **实时进度显示**：提供详细的下载和处理进度反馈

## 📋 系统要求

### 基础要求
- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+、macOS 10.14+、Ubuntu 18.04+ 或其他主流 Linux 发行版
- **内存**: 建议 4GB RAM 或更多（GPU 加速需要更多）
- **存储空间**: 至少 2GB 可用空间（用于模型和临时文件）

### 可选依赖
- **FFmpeg**: 用于音频格式转换（强烈推荐）
- **CUDA**: 用于 GPU 加速转录（可选，需要 NVIDIA GPU）

## 🚀 快速开始

### 1. 安装 FFmpeg（推荐）

**Windows:**
```bash
# 使用 Scoop（推荐）
scoop install ffmpeg

# 或使用 Chocolatey
choco install ffmpeg
```

**macOS:**
```bash
# 使用 Homebrew
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 2. 安装 Video Draft Creator

```bash
# 方法1: 使用 pip（推荐）
pip install video-draft-creator

# 方法2: 从源代码安装
git clone https://github.com/yourusername/video-draft-creator.git
cd video-draft-creator
pip install -e .
```

### 3. 初始化配置

```bash
# 创建配置文件
video-draft-creator config --init

# 查看配置示例
video-draft-creator config --show
```

### 4. 配置 DeepSeek API

编辑配置文件 `config/config.yaml`，设置您的 DeepSeek API 密钥：

```yaml
correction:
  api_key: "your_deepseek_api_key_here"
```

或者设置环境变量：
```bash
export DEEPSEEK_API_KEY="your_deepseek_api_key_here"
```

## 💡 使用示例

### 基础用法

```bash
# 下载并转录单个视频
video-draft-creator process "https://www.youtube.com/watch?v=VIDEO_ID" --transcribe

# 使用浏览器 Cookie 下载受限内容
video-draft-creator process "https://www.bilibili.com/video/BV1234567890" \
  --cookie-browser chrome --transcribe

# 指定输出目录和格式
video-draft-creator process "https://youtube.com/watch?v=VIDEO_ID" \
  --output-dir ./output --format markdown --transcribe --correct
```

### 批量处理

```bash
# 创建 URL 文件 urls.txt
echo "https://www.youtube.com/watch?v=VIDEO_ID1" > urls.txt
echo "https://www.youtube.com/watch?v=VIDEO_ID2" >> urls.txt

# 批量下载和转录
video-draft-creator batch urls.txt --transcribe --correct --max-workers 3
```

### 单独使用各个功能

```bash
# 仅转录已有音频文件
video-draft-creator transcribe audio.mp3 --model-size medium --language zh

# 仅纠错文本文件
video-draft-creator correct transcript.txt --language zh

# 生成文档格式
video-draft-creator format corrected_text.txt --formats markdown docx --title "会议记录"

# 生成摘要和关键词
video-draft-creator analyze transcript.txt --language zh
```

## 🛠️ 详细命令参考

### process 命令 - 处理单个视频

```bash
video-draft-creator process <URL> [选项]
```

**必需参数:**
- `URL`: 视频URL

**主要选项:**
- `--transcribe, -t`: 下载后进行转录
- `--correct`: 转录后进行AI文本纠错
- `--summarize`: 生成文本摘要
- `--keywords`: 提取关键词
- `--output-dir, -o DIR`: 输出目录
- `--output-name, -n NAME`: 输出文件名
- `--audio-quality, -q QUALITY`: 音频质量 (best/worst/128/192/256/320)
- `--format, -f FORMAT`: 输出格式 (markdown/txt/docx)
- `--cookie-browser BROWSER`: 浏览器Cookie (chrome/firefox/safari/edge/opera/brave)
- `--cookie-file FILE`: Cookie文件路径
- `--info-only`: 仅获取视频信息
- `--profile, -p PROFILE`: 使用配置预设
- `--verbose, -v`: 详细输出

### batch 命令 - 批量处理

```bash
video-draft-creator batch <文件路径> [选项]
```

**必需参数:**
- `文件路径`: 包含URL的文本文件路径

**主要选项:**
- `--max-workers, -w NUM`: 并行工作线程数 (默认: 3)
- `--sequential`: 使用顺序处理
- `--no-progress`: 禁用进度显示
- 其他选项同 process 命令

### transcribe 命令 - 音频转录

```bash
video-draft-creator transcribe <音频文件> [选项]
```

**选项:**
- `--model-size, -m SIZE`: 模型大小 (tiny/base/small/medium/large/large-v2/large-v3)
- `--language, -l LANG`: 音频语言 (zh/en/auto)
- `--format, -f FORMAT`: 输出格式 (srt/vtt/txt/all)
- `--output-dir, -o DIR`: 输出目录

### config 命令 - 配置管理

```bash
video-draft-creator config [选项]
```

**选项:**
- `--show`: 显示当前配置
- `--init`: 初始化配置文件
- `--test`: 测试配置
- `--list-profiles`: 列出配置预设
- `--save-profile NAME`: 保存当前配置为预设
- `--show-profile NAME`: 显示配置预设详情
- `--delete-profile NAME`: 删除配置预设

## ⚙️ 配置详解

### 配置文件结构

配置文件位置：`config/config.yaml`

```yaml
# DeepSeek API 配置
correction:
  api_key: "your_deepseek_api_key_here"
  api_endpoint: "https://api.deepseek.com/chat/completions"
  model: "deepseek-chat"
  max_retries: 3
  timeout: 30
  chunk_size: 2000

# 下载配置
download:
  output_dir: "./temp"
  audio_quality: "best"
  supported_formats: ["mp3", "wav", "m4a"]
  
  # Cookie 配置
  cookies:
    from_browser: "chrome"  # chrome, firefox, safari, edge, opera, brave
    cookie_file: null
    auto_captcha: true
  
  # 网络配置
  network:
    timeout: 30
    retries: 3
    user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# 转录配置
transcription:
  model_size: "medium"  # tiny, base, small, medium, large, large-v2, large-v3
  language: "auto"      # auto, zh, en, etc.
  temperature: 0.0
  beam_size: 5

# 输出配置
output:
  default_format: "markdown"
  include_timestamps: true
  include_summary: true
  include_keywords: true

# 日志配置
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "./logs/video_draft_creator.log"
```

### 环境变量

支持以下环境变量覆盖配置：

```bash
export DEEPSEEK_API_KEY="your_api_key"
export DEEPSEEK_API_ENDPOINT="https://api.deepseek.com/chat/completions"
export COOKIE_FILE="path/to/cookies.txt"
export COOKIES_FROM_BROWSER="chrome"
```

### 配置预设

创建和管理配置预设：

```bash
# 保存当前配置为预设
video-draft-creator config --save-profile "高质量转录" --description "使用大模型的高质量配置"

# 列出所有预设
video-draft-creator config --list-profiles

# 使用预设
video-draft-creator process "VIDEO_URL" --profile "高质量转录"
```

## 🔧 高级功能

### GPU 加速支持

#### 安装 CUDA 版本的 faster-whisper

```bash
# 卸载 CPU 版本
pip uninstall faster-whisper

# 安装 GPU 版本
pip install faster-whisper[gpu]

# 或者手动安装 CUDA 依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install faster-whisper
```

#### 验证 GPU 支持

```bash
# Python 中验证
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

#### GPU 配置优化

在配置文件中启用 GPU 优化：

```yaml
transcription:
  model_size: "large-v3"  # 使用最大模型以充分利用 GPU
  temperature: 0.0
  beam_size: 5
  # GPU 特定配置会自动检测并应用
```

### Cookie 管理最佳实践

#### 浏览器 Cookie 导入

```bash
# 支持的浏览器
video-draft-creator process "URL" --cookie-browser chrome    # Google Chrome
video-draft-creator process "URL" --cookie-browser firefox   # Mozilla Firefox  
video-draft-creator process "URL" --cookie-browser safari    # Safari (macOS)
video-draft-creator process "URL" --cookie-browser edge      # Microsoft Edge
video-draft-creator process "URL" --cookie-browser opera     # Opera
video-draft-creator process "URL" --cookie-browser brave     # Brave Browser
```

#### Cookie 文件使用

```bash
# 导出浏览器 Cookie 为 Netscape 格式
# 然后使用 Cookie 文件
video-draft-creator process "URL" --cookie-file cookies.txt
```

### 批量处理最佳实践

#### URL 文件格式

创建 `urls.txt` 文件：
```text
# 这是注释，会被忽略
https://www.youtube.com/watch?v=VIDEO_ID1
https://www.bilibili.com/video/BV1234567890

# 支持空行分隔
https://www.youtube.com/watch?v=VIDEO_ID2
```

#### 并行处理调优

```bash
# 根据系统配置调整并行度
video-draft-creator batch urls.txt --max-workers 2  # CPU 密集型系统
video-draft-creator batch urls.txt --max-workers 4  # 平衡配置
video-draft-creator batch urls.txt --max-workers 8  # 高性能系统

# 顺序处理（避免并发问题）
video-draft-creator batch urls.txt --sequential
```

## 🐛 常见问题与故障排除

### 下载相关问题

**问题**: 下载失败，提示"需要登录"
```
解决方案:
1. 使用浏览器 Cookie: --cookie-browser chrome
2. 导出并使用 Cookie 文件: --cookie-file cookies.txt
3. 确保已在浏览器中登录对应平台
```

**问题**: 某些平台不支持
```
解决方案:
1. 检查 yt-dlp 支持的平台列表
2. 更新 yt-dlp: pip install --upgrade yt-dlp
3. 尝试不同的 URL 格式
```

### 转录相关问题

**问题**: 转录速度过慢
```
解决方案:
1. 使用更小的模型: --model-size small
2. 启用 GPU 加速（如有 NVIDIA GPU）
3. 减少并行处理数量
```

**问题**: 转录精度不够
```
解决方案:
1. 使用更大的模型: --model-size large-v3
2. 指定正确的语言: --language zh 或 --language en
3. 确保音频质量良好
```

**问题**: GPU 内存不足
```
解决方案:
1. 使用较小的模型: --model-size medium
2. 减少 beam_size 参数
3. 关闭其他 GPU 应用程序
```

### API 相关问题

**问题**: DeepSeek API 调用失败
```
解决方案:
1. 检查 API 密钥是否正确设置
2. 确认网络连接正常
3. 检查 API 余额是否充足
4. 尝试降低请求频率
```

**问题**: API 响应超时
```
解决方案:
1. 增加超时时间: timeout: 60
2. 减少文本块大小: chunk_size: 1000
3. 检查网络稳定性
```

### 配置相关问题

**问题**: 配置文件找不到
```
解决方案:
1. 运行: video-draft-creator config --init
2. 确保配置文件路径正确
3. 检查文件权限
```

**问题**: 输出目录权限错误
```
解决方案:
1. 确保有写入权限: chmod 755 output_directory
2. 更换输出目录位置
3. 以管理员身份运行（Windows）
```

### 性能优化建议

**针对 CPU 优化:**
```bash
# 减少并行度
video-draft-creator batch urls.txt --max-workers 2

# 使用较小的转录模型
video-draft-creator transcribe audio.mp3 --model-size small
```

**针对内存优化:**
```yaml
# 在配置文件中设置
correction:
  chunk_size: 1000  # 减少文本块大小

transcription:
  model_size: "small"  # 使用较小模型
```

**针对网络优化:**
```yaml
download:
  network:
    timeout: 60      # 增加超时时间
    retries: 5       # 增加重试次数
```

## 📚 API 文档

本项目提供了完整的 API 文档，您可以：

1. **查看在线文档**: [API Documentation](docs/api/index.html)
2. **本地构建文档**: 
   ```bash
   # 安装文档依赖
   pip install sphinx sphinx-rtd-theme
   
   # 构建文档
   cd docs
   make html
   ```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/video-draft-creator.git
cd video-draft-creator

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 运行代码检查
flake8 src/
black src/
```

### 提交代码

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 🆘 获取帮助

- **问题报告**: [GitHub Issues](https://github.com/yourusername/video-draft-creator/issues)
- **功能请求**: [GitHub Discussions](https://github.com/yourusername/video-draft-creator/discussions)
- **文档**: [项目 Wiki](https://github.com/yourusername/video-draft-creator/wiki)

## 📝 更新日志

### v0.1.0 (2024-XX-XX)
- 🎉 初始版本发布
- ✨ 支持多平台视频下载
- ✨ 集成 faster-whisper 转录
- ✨ DeepSeek API 文本纠错
- ✨ 多格式文档输出
- ✨ 批量处理和并行下载

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 🙏 致谢

感谢以下开源项目的支持：

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载工具
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 高效的语音转录
- [DeepSeek](https://www.deepseek.com/) - 强大的 AI 语言模型
- [click](https://click.palletsprojects.com/) - 优秀的命令行界面库

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！** 