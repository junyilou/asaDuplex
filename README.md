# asaDuplex
![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
[![Jobs at Apple](https://github.com/junyilou/asaDuplex/actions/workflows/jobs-global.yaml/badge.svg)](https://github.com/junyilou/asaDuplex/actions/workflows/jobs-global.yaml)
[![Today at Apple](https://github.com/junyilou/asaDuplex/actions/workflows/today-normal.yaml/badge.svg)](https://github.com/junyilou/asaDuplex/actions/workflows/today-normal.yaml)

![bot](Retail/bot.jpg)

一个以**异步**和**面向对象**思想编写的 Apple Store 零售店 Python 库。

**asaDuplex 提供了全球超过 500 家零售店的详细信息**，并对他们进行 Python 包装。你可以：

* 模糊、精确按城市、国家、名称、编号搜索全球已开业、关闭、内部 Apple Store 零售店
* 以极高效的方式查询 Apple Store 零售店的详细信息，包括开业和搬迁或关闭日期、营业时间和特别营业时间、当地时区和现在时间、详细地址和经纬度坐标等
* 以极快的速度查询 Today at Apple 课程、排课信息，包括轻松获取课程介绍、配图和视频地址，跨店、跨国查询排课，搜索还未排课的未来特别活动等
* 通过模块化设计的各种函数，实现信息的定时追踪，例如定期查询指定零售店的特别营业时间、定期查询零售店官方照片的变更、获取新 Today at Apple 课程详细信息、获取正在招聘的未开业零售店等

果铺知道通过库中的代码实现了 Telegram 果铺知道 Bot，你可以在[这里](https://t.me/guopuzdbot)体验。



### 代码依赖

代码使用了最高至 Python 3.12 的语法和特性，**必须使用 Python 3.12 版本才可完整运行**

所有网络请求均使用异步网络 I/O: [aiohttp](https://github.com/aio-libs/aiohttp) 发送，部分代码依赖 [beautifulsoup4](https://pypi.org/project/beautifulsoup4) 和 [lxml](https://github.com/lxml/lxml)，可通过 pip 安装

#### Webhooks

许多代码设计为将结果输出推送通知，这些代码通常导入了以下模块：

```python
from bot import chat_ids
from botpost import async_post
```

库中给出了一个示例 [bot.py](bot.py) 和 [botpost.py](botpost.py)，将读取环境变量 `BOTPOST_CHAT_ID` 中的用户 ID 和 `BOTPOST_API` 中的 Webhooks API 地址进行推送，你可以修改为其他你自己的结果推送方式。



### 库历史

2019 年 6 月：迁移库并命名 asaDuplex。[[commit]](https://github.com/junyilou/asaduplex/commit/e405a00ab74969a7dcacb719bdab2847e59becb8)

2019 年 8 月：升级 Python 3。[[commit]](https://github.com/junyilou/asaduplex/commit/a6ac48353a318586751e4a7f901c8c4d2692b26d)

2019 年 11 月：从后期常态占用改为配合 cron 计划任务。[[commit]](https://github.com/junyilou/asaduplex/commit/6ca8a09d112fe3a67ac1d28f53ec6446f99b83e7)

2020 年 11 月：将推送通知从 IFTTT 改为 Telegram Bot，同时支持富文本和多媒体输出。[[commit]](https://github.com/junyilou/asaduplex/commit/bd1acf74a33dcb44c2076d1aac67559b547d7a0b)

2021 年 3 月：利用 asaDuplex 中的部分代码，推出果铺知道 Telegram Bot，方便用户快速查询 Apple Store 零售店信息及特别营业时间信息。

2021 年 8 月：进一步模块化代码，并将代码结果推送剥离，不再依赖 Telegram Bot 做结果推送。[[commit]](https://github.com/junyilou/asaduplex/commit/9537444cadaf4b6b989ff26f3b2313f3aaf8c17c)

2022 年 3 月：使用 asyncio、aiohttp 异步化核心代码，极大幅度的提高运行速度。[[commit]](https://github.com/junyilou/asaduplex/commit/6c7e3b729ab1ced4a8ae8888a5930fc55df8319e)

2022 年 4 月：面向对象化 Today at Apple。[[commit]](https://github.com/junyilou/asaduplex/commit/4d98ae7f00312630479243184e715c929afd5b7a)

2022 年 10 月：改进代码使用 Python 3.8 [[commit]](https://github.com/junyilou/asaduplex/commit/2e7511ed22c38b7272f5b3e041ed6d66f8dcf21c), Python 3.9 [[commit]](https://github.com/junyilou/asaduplex/commit/dcfa943e543c157ca14a7e14cf98c98732ffc400), Python 3.10 [[commit]](https://github.com/junyilou/asaduplex/commit/78543f98a8c22b3aa6b93d6bc14d76b5f217e027), Python 3.11 [[commit]](https://github.com/junyilou/asaduplex/commit/9a3cf1cb049f0587b9dbb5a85500b26b6d77704e) 的部分特性。

2022 年 11 月：面向对象化 storeInfo 核芯。 [[commit]](https://github.com/junyilou/asaduplex/commit/49ee12f2785bd4a12637321abc72808d859e585b)

2023 年 11 月：重写了核心网络请求函数，并适配了 Python 3.12 的部分特性。[[commit1]](https://github.com/junyilou/asaDuplex/commit/3d256965e798e501563120b3133b40883745945d) [[commit2]](https://github.com/junyilou/asaDuplex/commit/26c479a1c2b61bea518893b0f20d82ba18158e3e)

2024 年 6 月：使用 GitHub Actions 自动化 Jobs at Apple 和 Today at Apple。[[commit1]](https://github.com/junyilou/asaDuplex/commit/18f9bb670f4de4809f927fb105b6f2b462f7391a) [[commit2]](https://github.com/junyilou/asaDuplex/commit/515eb0540610ccc509b9a422e863013befd5af80)


##### 免责声明 | Disclaimer

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。未经特别授权应仅作个人兴趣用途。有关更多 Apple 商标和内容使用细则，请参见 Apple 法律信息及其知识产权页面。

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. No part unless explicit authorizations should be used for any purpose other than personal interests. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its IP websites.