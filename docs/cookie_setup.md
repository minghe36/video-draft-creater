# Cookie配置指南

## 为什么需要Cookie？

许多视频平台（特别是YouTube）现在需要Cookie来验证用户身份，避免被识别为机器人。如果没有Cookie验证，可能会遇到以下错误：

- `HTTP Error 403: Forbidden`
- `Sign in to confirm you're not a bot`
- `需要登录验证`

## 配置方法

### 方法1: 从浏览器导入Cookie（推荐）

这是最简单的方法，工具会自动从你的浏览器中读取Cookie。

#### 在配置文件中设置
```yaml
download:
  cookies:
    from_browser: "chrome"  # 支持: chrome, firefox, safari, edge, opera, brave
    cookie_file: null
    auto_captcha: true
```

#### 在命令行中使用
```bash
# 使用Chrome浏览器的Cookie
python -m video_draft_creator.cli process "https://www.youtube.com/watch?v=VIDEO_ID" --cookie-browser chrome

# 使用Firefox浏览器的Cookie
python -m video_draft_creator.cli process "https://www.youtube.com/watch?v=VIDEO_ID" --cookie-browser firefox
```

### 方法2: 使用Cookie文件

如果浏览器方式不可用，可以手动导出Cookie文件。

#### 1. 导出Cookie文件

**从Chrome导出：**
1. 安装Chrome扩展 "Get cookies.txt"
2. 访问YouTube并登录
3. 点击扩展图标，导出cookies.txt

**从Firefox导出：**
1. 安装Firefox扩展 "cookies.txt"
2. 访问YouTube并登录
3. 导出cookies.txt文件

#### 2. 配置Cookie文件路径

在配置文件中：
```yaml
download:
  cookies:
    from_browser: null
    cookie_file: "./cookies.txt"  # Cookie文件路径
    auto_captcha: true
```

在命令行中：
```bash
python -m video_draft_creator.cli process "https://www.youtube.com/watch?v=VIDEO_ID" --cookie-file "./cookies.txt"
```

## 支持的浏览器

- **Chrome** - `chrome`
- **Firefox** - `firefox` 
- **Safari** - `safari` (仅macOS)
- **Edge** - `edge`
- **Opera** - `opera`
- **Brave** - `brave`

## 常见问题

### Q: 浏览器Cookie导入失败怎么办？

**解决方案：**
1. 确保浏览器已关闭（某些系统需要）
2. 确保你在浏览器中已登录相应平台
3. 尝试使用Cookie文件方式

### Q: 仍然提示需要验证怎么办？

**解决方案：**
1. 确保在浏览器中能正常访问该视频
2. 尝试访问一下视频页面以"激活"Cookie
3. 检查Cookie文件是否包含相应平台的认证信息

### Q: 不同平台需要不同的Cookie吗？

**回答：** 是的，不同平台的Cookie是独立的：
- YouTube: 需要google.com的Cookie
- Bilibili: 需要bilibili.com的Cookie
- 其他平台: 需要对应域名的Cookie

### Q: Cookie会过期吗？

**回答：** 会的，Cookie通常有过期时间：
- 建议定期重新登录网站刷新Cookie
- 使用浏览器导入方式会自动获取最新Cookie
- Cookie文件需要手动更新

## 安全提示

⚠️ **Cookie包含敏感信息，请注意保护：**

1. **不要分享Cookie文件** - 包含你的登录凭据
2. **定期更新Cookie** - 避免使用过期的认证信息
3. **安全存储** - 将Cookie文件放在安全位置
4. **使用后删除** - 在公共设备上使用完后删除Cookie文件

## 测试Cookie配置

运行测试命令验证Cookie配置：

```bash
# 测试基本功能
python -m video_draft_creator.cli test

# 测试特定Cookie配置
python -m video_draft_creator.cli test --cookie-browser chrome

# 仅获取视频信息（测试Cookie是否有效）
python -m video_draft_creator.cli process "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --info-only --cookie-browser chrome
```

## 示例配置

### 完整配置文件示例
```yaml
# config/config.yaml
download:
  output_dir: "./downloads"
  audio_quality: "best"
  
  # Cookie配置
  cookies:
    from_browser: "chrome"      # 从Chrome导入
    cookie_file: null          # 不使用文件
    auto_captcha: true         # 自动处理验证
  
  # 网络配置
  network:
    timeout: 30
    retries: 3
    user_agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### 批量下载示例
```bash
# 创建URL列表文件 urls.txt
echo "https://www.youtube.com/watch?v=VIDEO1" > urls.txt
echo "https://www.youtube.com/watch?v=VIDEO2" >> urls.txt

# 批量下载
python -m video_draft_creator.cli batch urls.txt --cookie-browser chrome
```

这样配置后，你就可以绕过大部分平台的验证限制，顺利下载视频音频了！ 