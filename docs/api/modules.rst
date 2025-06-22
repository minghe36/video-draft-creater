API 模块概览
=============

Video Draft Creator 由以下核心模块组成：

核心模块
--------

.. toctree::
   :maxdepth: 1

   downloader
   transcriber
   corrector
   output_formatter
   cli
   config
   progress

模块架构
--------

Video Draft Creator 采用模块化设计，每个模块负责特定的功能：

数据流程
^^^^^^^^

.. code-block:: text

   URL 输入 → 下载器 → 音频文件 → 转录器 → 文本 → 纠错器 → 结构化文本 → 格式化器 → 最终文档

核心组件
^^^^^^^^

- **downloader**: 负责从各种视频平台下载音频
- **transcriber**: 使用 faster-whisper 进行语音转录
- **corrector**: 使用 DeepSeek API 进行文本纠错和分析
- **output_formatter**: 生成多种格式的文档输出
- **cli**: 提供命令行界面
- **config**: 配置管理
- **progress**: 进度显示和用户交互

依赖关系
^^^^^^^^

.. code-block:: text

   cli
   ├── config
   ├── downloader
   │   └── progress
   ├── transcriber
   │   └── progress
   ├── corrector
   └── output_formatter

快速导入
--------

.. code-block:: python

   from video_draft_creator import (
       create_downloader,
       create_transcriber,
       create_corrector_from_config,
       create_formatter
   )

完整的 API 参考请查看各个模块的详细文档。 