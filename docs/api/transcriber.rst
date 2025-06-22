transcriber 模块
================

.. automodule:: video_draft_creator.transcriber
   :members:
   :undoc-members:
   :show-inheritance:

AudioTranscriber 类
--------------------

.. autoclass:: video_draft_creator.transcriber.AudioTranscriber
   :members:
   :undoc-members:
   :show-inheritance:

   基于 faster-whisper 的高精度语音转录器。

   .. note::
      支持的模型大小：
      
      - tiny: 最快，准确度较低
      - base: 平衡速度和准确度
      - small: 中等速度，较高准确度
      - medium: 默认选择，良好平衡
      - large: 最高准确度，速度较慢
      - large-v2: 改进的大模型
      - large-v3: 最新的大模型

工厂函数
--------

.. autofunction:: video_draft_creator.transcriber.create_transcriber

使用示例
--------

基础转录
^^^^^^^^

.. code-block:: python

   from video_draft_creator.transcriber import create_transcriber

   # 创建转录器
   transcriber = create_transcriber(
       model_size="medium",
       language="zh"
   )
   
   # 转录音频文件
   result = transcriber.transcribe("audio.mp3")
   
   print("转录文本:", result['text'])
   print("语言:", result['language'])
   print("置信度:", result['confidence'])

自定义配置
^^^^^^^^^^

.. code-block:: python

   transcriber = create_transcriber(
       model_size="large-v3",
       language="auto",  # 自动检测语言
       temperature=0.0,  # 确定性输出
       beam_size=5      # 束搜索大小
   )

输出格式
^^^^^^^^

.. code-block:: python

   # 获取带时间戳的字幕
   segments = transcriber.get_segments("audio.mp3")
   
   for segment in segments:
       print(f"[{segment['start']:.2f}s - {segment['end']:.2f}s]: {segment['text']}")
   
   # 导出为SRT格式
   srt_content = transcriber.to_srt("audio.mp3")
   
   # 导出为VTT格式
   vtt_content = transcriber.to_vtt("audio.mp3")

进度回调
^^^^^^^^

.. code-block:: python

   def progress_callback(segment_count, segment):
       print(f"处理第 {segment_count} 个片段: {segment['text'][:50]}...")
   
   result = transcriber.transcribe(
       "audio.mp3",
       progress_callback=progress_callback
   )

GPU 加速
^^^^^^^^

.. code-block:: python

   # GPU 加速会自动检测并启用
   # 确保安装了 CUDA 版本的 PyTorch
   transcriber = create_transcriber(
       model_size="large-v3",  # 大模型可以充分利用GPU
       device="cuda"  # 明确指定使用GPU
   )

异常处理
--------

.. autoexception:: video_draft_creator.transcriber.TranscriptionError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.transcriber.ModelLoadError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.transcriber.AudioFormatError
   :members:
   :show-inheritance: 