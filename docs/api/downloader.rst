downloader 模块
===============

.. automodule:: video_draft_creator.downloader
   :members:
   :undoc-members:
   :show-inheritance:

VideoDownloader 类
-------------------

.. autoclass:: video_draft_creator.downloader.VideoDownloader
   :members:
   :undoc-members:
   :show-inheritance:

   主要负责从各种视频平台下载音频文件。

   .. note::
      VideoDownloader 支持以下平台：
      
      - YouTube
      - Bilibili
      - 其他 yt-dlp 支持的平台

工厂函数
--------

.. autofunction:: video_draft_creator.downloader.create_downloader

使用示例
--------

基础使用
^^^^^^^^

.. code-block:: python

   from video_draft_creator.downloader import create_downloader
   from video_draft_creator.config import load_config

   # 创建下载器
   downloader = create_downloader()
   
   # 加载配置
   config = load_config()
   downloader.config = config
   
   # 检查URL支持
   supported, platform = downloader.check_url_support("https://www.youtube.com/watch?v=VIDEO_ID")
   
   if supported:
       # 下载音频
       success, message, file_path = downloader.download_audio(
           "https://www.youtube.com/watch?v=VIDEO_ID",
           "output_name"
       )

使用Cookie
^^^^^^^^^^

.. code-block:: python

   # 配置浏览器Cookie
   config.download.cookies.from_browser = "chrome"
   
   # 或使用Cookie文件
   config.download.cookies.cookie_file = "cookies.txt"
   
   # 下载受限内容
   success, message, file_path = downloader.download_audio(url, name)

批量下载
^^^^^^^^

.. code-block:: python

   urls = [
       "https://www.youtube.com/watch?v=VIDEO_ID1",
       "https://www.youtube.com/watch?v=VIDEO_ID2"
   ]
   
   results = downloader.batch_download(urls, max_workers=3)
   
   for result in results:
       if result['success']:
           print(f"下载成功: {result['file_path']}")
       else:
           print(f"下载失败: {result['error']}")

异常处理
--------

.. autoexception:: video_draft_creator.downloader.DownloadError
   :members:
   :show-inheritance:

.. autoexception:: video_draft_creator.downloader.UnsupportedPlatformError
   :members:
   :show-inheritance: 