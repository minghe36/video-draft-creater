cli 模块
========

.. automodule:: video_draft_creator.cli
   :members:
   :undoc-members:
   :show-inheritance:

命令行接口概览
--------------

Video Draft Creator 提供了丰富的命令行接口，支持从视频下载到文档生成的完整工作流程。

主要命令
--------

process 命令
^^^^^^^^^^^^

处理单个视频的完整工作流程。

.. code-block:: bash

   video-draft-creator process URL [options]

常用选项：

- ``--transcribe``: 启用语音转录
- ``--correct``: 启用文本纠错
- ``--summary``: 生成摘要
- ``--keywords``: 提取关键词
- ``--format FORMAT``: 指定输出格式 (markdown, txt, docx, srt, vtt)
- ``--output PATH``: 指定输出路径
- ``--config PATH``: 使用指定配置文件

batch 命令
^^^^^^^^^^

批量处理多个视频。

.. code-block:: bash

   video-draft-creator batch [options]

常用选项：

- ``--input-file FILE``: 从文件读取URL列表
- ``--urls URL1 URL2 ...``: 直接指定多个URL
- ``--max-workers N``: 并行处理数量
- ``--delay SECONDS``: 处理间隔

transcribe 命令
^^^^^^^^^^^^^^^

仅进行音频转录。

.. code-block:: bash

   video-draft-creator transcribe INPUT [options]

常用选项：

- ``--model-size SIZE``: 指定模型大小
- ``--language LANG``: 指定语言
- ``--output-format FORMAT``: 输出格式

config 命令
^^^^^^^^^^^

配置管理。

.. code-block:: bash

   video-draft-creator config [subcommand] [options]

子命令：

- ``show``: 显示当前配置
- ``set KEY VALUE``: 设置配置项
- ``reset``: 重置配置
- ``validate``: 验证配置

函数参考
--------

.. autofunction:: video_draft_creator.cli.main

.. autofunction:: video_draft_creator.cli.process_command

.. autofunction:: video_draft_creator.cli.batch_command

.. autofunction:: video_draft_creator.cli.transcribe_command

.. autofunction:: video_draft_creator.cli.config_command

命令行参数解析
--------------

.. autofunction:: video_draft_creator.cli.create_parser

.. autofunction:: video_draft_creator.cli.parse_arguments

错误处理
--------

.. autoexception:: video_draft_creator.cli.CLIError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.cli.CommandError
   :members:
   :show-inheritance:

使用示例
--------

完整工作流程
^^^^^^^^^^^^

.. code-block:: bash

   # 下载、转录、纠错并生成Markdown文档
   video-draft-creator process "https://www.youtube.com/watch?v=VIDEO_ID" \
     --transcribe --correct --summary --keywords \
     --format markdown --output "video_transcript.md"

批量处理
^^^^^^^^

.. code-block:: bash

   # 从文件批量处理
   video-draft-creator batch --input-file urls.txt \
     --transcribe --correct --max-workers 3

   # 直接指定多个URL
   video-draft-creator batch \
     --urls "https://url1.com" "https://url2.com" \
     --transcribe --format txt

音频转录
^^^^^^^^

.. code-block:: bash

   # 转录音频文件
   video-draft-creator transcribe audio.mp3 \
     --model-size large --language zh \
     --output-format srt

配置管理
^^^^^^^^

.. code-block:: bash

   # 查看当前配置
   video-draft-creator config show
   
   # 设置API密钥
   video-draft-creator config set correction.api_key "your_api_key"
   
   # 重置配置
   video-draft-creator config reset

高级用法
^^^^^^^^

.. code-block:: bash

   # 使用自定义配置文件
   video-draft-creator process URL \
     --config custom_config.yaml \
     --transcribe --correct
   
   # 使用浏览器Cookie
   video-draft-creator process URL \
     --cookie-browser chrome \
     --transcribe
   
   # 指定输出目录和文件名
   video-draft-creator process URL \
     --output-dir ./outputs \
     --output-name "custom_name" \
     --format docx 