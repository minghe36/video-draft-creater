Video Draft Creator Documentation
===================================

.. image:: https://img.shields.io/badge/python-3.8+-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.8+

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :target: https://github.com/yourusername/video-draft-creator/blob/main/LICENSE
   :alt: MIT License

一个基于 Python 的强大命令行工具，专为从流媒体视频中提取音频、进行高精度语音转录并生成经过 AI 纠错的结构化文稿而设计。

特性概览
--------

* 🎥 **多平台视频音频下载**：使用 yt-dlp 支持 YouTube、B站、优酷等主流视频平台
* 🍪 **智能 Cookie 管理**：支持 6 大主流浏览器的 Cookie 自动导入
* 🎤 **高精度语音转录**：基于 faster-whisper 实现快速、准确的语音转文字
* 🤖 **AI 智能纠错**：集成 DeepSeek API 进行智能文本纠错和结构化
* 📊 **智能文本分析**：自动生成摘要、提取关键词和主题分析
* 📄 **多格式输出**：支持 Markdown、TXT、DOCX、SRT、VTT 等多种输出格式

快速开始
--------

安装
^^^^

.. code-block:: bash

   pip install video-draft-creator

基础使用
^^^^^^^^

.. code-block:: bash

   # 下载并转录单个视频
   video-draft-creator process "https://www.youtube.com/watch?v=VIDEO_ID" --transcribe

   # 使用浏览器 Cookie 下载受限内容
   video-draft-creator process "https://www.bilibili.com/video/BV1234567890" \
     --cookie-browser chrome --transcribe

用户指南
--------

.. toctree::
   :maxdepth: 2
   :caption: 用户指南

   installation
   configuration
   usage
   troubleshooting

API 参考
--------

.. toctree::
   :maxdepth: 2
   :caption: API 参考

   api/modules
   api/downloader
   api/transcriber
   api/corrector
   api/output_formatter
   api/cli

开发者指南
----------

.. toctree::
   :maxdepth: 2
   :caption: 开发者指南

   development/setup
   development/contributing
   development/testing

索引和表格
----------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search` 