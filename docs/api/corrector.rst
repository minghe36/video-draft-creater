corrector 模块
==============

.. automodule:: video_draft_creator.corrector
   :members:
   :undoc-members:
   :show-inheritance:

TextCorrector 类
-----------------

.. autoclass:: video_draft_creator.corrector.TextCorrector
   :members:
   :undoc-members:
   :show-inheritance:

   基于 DeepSeek API 的智能文本纠错和分析器。

   .. note::
      支持的功能：
      
      - 文本纠错和标准化
      - 自动摘要生成
      - 关键词提取
      - 主题分析
      - 情感分析

工厂函数
--------

.. autofunction:: video_draft_creator.corrector.create_corrector_from_config

使用示例
--------

基础纠错
^^^^^^^^

.. code-block:: python

   from video_draft_creator.corrector import create_corrector_from_config
   from video_draft_creator.config import load_config

   # 从配置创建纠错器
   config = load_config()
   corrector = create_corrector_from_config(config)
   
   # 纠错文本
   raw_text = "这是一个包含错误和语言表达不当的转录文本..."
   corrected_text = corrector.correct_text(raw_text)
   
   print("原文:", raw_text)
   print("纠错后:", corrected_text)

分块处理
^^^^^^^^

.. code-block:: python

   # 长文本自动分块处理
   long_text = "很长的转录文本..." * 1000
   
   corrected_text = corrector.correct_text(
       long_text,
       chunk_size=2000  # 每块2000字符
   )

智能分析
^^^^^^^^

.. code-block:: python

   # 生成摘要
   summary = corrector.generate_summary(text, max_length=200)
   
   # 提取关键词
   keywords = corrector.extract_keywords(text, max_keywords=10)
   
   # 主题分析
   topics = corrector.analyze_topics(text)
   
   print("摘要:", summary)
   print("关键词:", keywords)
   print("主题:", topics)

完整分析
^^^^^^^^

.. code-block:: python

   # 一次性完成所有分析
   result = corrector.comprehensive_analysis(
       text,
       include_summary=True,
       include_keywords=True,
       include_topics=True,
       max_summary_length=300,
       max_keywords=15
   )
   
   print("纠错文本:", result['corrected_text'])
   print("摘要:", result['summary'])
   print("关键词:", result['keywords'])
   print("主题:", result['topics'])

进度回调
^^^^^^^^

.. code-block:: python

   def progress_callback(current, total, stage):
       print(f"{stage}: {current}/{total}")
   
   corrected_text = corrector.correct_text(
       long_text,
       progress_callback=progress_callback
   )

自定义参数
^^^^^^^^^^

.. code-block:: python

   corrector = TextCorrector(
       api_key="your_api_key",
       api_endpoint="https://api.deepseek.com/chat/completions",
       model="deepseek-chat",
       max_retries=5,
       timeout=60,
       chunk_size=1500
   )

异常处理
--------

.. autoexception:: video_draft_creator.corrector.CorrectionError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.corrector.APIError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.corrector.ConfigurationError
   :members:
   :show-inheritance: 