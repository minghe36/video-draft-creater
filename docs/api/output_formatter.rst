output_formatter 模块
=====================

.. automodule:: video_draft_creator.output_formatter
   :members:
   :undoc-members:
   :show-inheritance:

OutputFormatter 类
-------------------

.. autoclass:: video_draft_creator.output_formatter.OutputFormatter
   :members:
   :undoc-members:
   :show-inheritance:

   多格式文档输出生成器。

   .. note::
      支持的输出格式：
      
      - Markdown (.md)
      - 纯文本 (.txt)
      - Microsoft Word (.docx)
      - SubRip 字幕 (.srt)
      - WebVTT 字幕 (.vtt)

工厂函数
--------

.. autofunction:: video_draft_creator.output_formatter.create_formatter

使用示例
--------

基础用法
^^^^^^^^

.. code-block:: python

   from video_draft_creator.output_formatter import create_formatter

   # 创建格式化器
   formatter = create_formatter()
   
   # 准备文档数据
   doc_data = {
       'title': '视频标题',
       'url': 'https://example.com/video',
       'transcript': '转录文本...',
       'corrected_text': '纠错后的文本...',
       'summary': '视频摘要...',
       'keywords': ['关键词1', '关键词2'],
       'segments': [
           {'start': 0.0, 'end': 5.0, 'text': '第一段文本'},
           {'start': 5.0, 'end': 10.0, 'text': '第二段文本'}
       ]
   }
   
   # 生成Markdown文档
   markdown_content = formatter.to_markdown(doc_data)
   
   # 保存文档
   formatter.save_document(doc_data, 'output.md', 'markdown')

多格式输出
^^^^^^^^^^

.. code-block:: python

   # 生成不同格式的文档
   formats = ['markdown', 'txt', 'docx', 'srt', 'vtt']
   
   for fmt in formats:
       output_file = f"output.{fmt}"
       formatter.save_document(doc_data, output_file, fmt)

Markdown 格式
^^^^^^^^^^^^^

.. code-block:: python

   # 自定义Markdown选项
   markdown_content = formatter.to_markdown(
       doc_data,
       include_toc=True,        # 包含目录
       include_metadata=True,   # 包含元数据
       include_timestamps=True  # 包含时间戳
   )

Word文档
^^^^^^^^

.. code-block:: python

   # 生成Word文档
   docx_content = formatter.to_docx(
       doc_data,
       include_styles=True,     # 应用样式
       include_headers=True     # 包含页眉页脚
   )

字幕文件
^^^^^^^^

.. code-block:: python

   # 生成SRT字幕
   srt_content = formatter.to_srt(doc_data['segments'])
   
   # 生成VTT字幕
   vtt_content = formatter.to_vtt(doc_data['segments'])
   
   # 保存字幕文件
   with open('subtitles.srt', 'w', encoding='utf-8') as f:
       f.write(srt_content)

批量处理
^^^^^^^^

.. code-block:: python

   # 批量生成多个文档
   document_list = [doc_data1, doc_data2, doc_data3]
   
   results = formatter.batch_generate(
       document_list,
       output_dir='./outputs',
       formats=['markdown', 'txt'],
       name_template='{title}_{timestamp}'
   )

自定义模板
^^^^^^^^^^

.. code-block:: python

   # 使用自定义模板
   custom_template = '''
   # {title}
   
   **原始链接**: {url}
   **处理时间**: {timestamp}
   
   ## 内容摘要
   {summary}
   
   ## 完整文本
   {corrected_text}
   '''
   
   # 应用自定义模板
   formatter.set_template('markdown', custom_template)
   result = formatter.to_markdown(doc_data)

配置选项
^^^^^^^^

.. code-block:: python

   # 配置格式化选项
   formatter.configure({
       'markdown': {
           'heading_style': 'atx',     # ATX标题样式 (#)
           'code_style': 'fenced',     # 围栏代码块
           'table_style': 'grid'       # 表格样式
       },
       'docx': {
           'font_name': 'SimSun',      # 字体
           'font_size': 12,            # 字号
           'line_spacing': 1.5         # 行距
       }
   })

异常处理
--------

.. autoexception:: video_draft_creator.output_formatter.FormattingError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.output_formatter.TemplateError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.output_formatter.FileWriteError
   :members:
   :show-inheritance: 