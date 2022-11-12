# asaDuplex ![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)

![bot](Retail/bot.jpg)

\* asaDuplex 尚不开源 Telegram Bot 的运行代码，您可以在[这里](https://t.me/guopuzdbot)进行体验。

## 仓库内容

#### 代码

* allBands.py: 获得全部在售 Apple Watch 表带基本信息
* Hours.py: 取得 Apple Store 特别营业时间信息
* Jobs.py: 取得全球 Apple 零售招聘情况以获得未来新店
* Rtl.py: 取得 Apple Store 零售店服务器图片更新
* Today.py: 取得最新 Today at Apple 活动

#### 模块

* storeInfo.py: 处理 storeInfo.json 的数据，提供强大的通用函数
* modules/special.py: 分析 Apple Store 零售店营业时间，并尝试获得特别营业时间内部备忘录
* modules/today.py: 一个定义了 Today at Apple 课程、排课、零售店对象的模块
* modules/constants.py: 保存部分常量
* modules/util.py: 保存部分通用函数

#### 文本

* allBands.json: 由 allBands.py 生成的找到的表带信息
* savedEvent.json: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedJobs.json: 由 Jobs.py 生成的，已经在检测到招聘的零售店编号
* storeInfo.json: 全球 Apple Store 名称（包含部分曾用名、ASCII 兼容名等以便于更广的匹配）、店号、国家或地区旗帜、开店时间、官网图片最后修改时间、URL 标签、全球各国地区零售店按行政区划字典、用于模糊搜索的关键字 alias 等



## 代码依赖

本库中的部分代码使用了 Python 3.8 至 Python 3.11 的部分特性，建议使用尽可能新的 Python 3 运行。

本代码的网络 I/O 请求依赖 [aiohttp](https://github.com/aio-libs/aiohttp)，可通过 pip 安装，库中需要网络请求的函数全部为协程函数，需要使用 `await` 关键字等待，但也提供了简单的异步转同步方法 `sync()`，可在复杂度不高的代码中使用。

```python
from modules.special import speHours
from modules.util import sync

>>> await speHours(session=None, sid=688) # 异步
{'2022-10-15': {'regular': '10:00 - 23:00', 'special': '10:00 - 22:00', 'reason': '[COVID Related]'}}

>>> sync(speHours(session=None, sid=688)) # 同步，不建议
{'2022-10-15': {'regular': '10:00 - 23:00', 'special': '10:00 - 22:00', 'reason': '[COVID Related]'}}
```



## 如何利用

* storeInfo.json 提供了极为丰富的 Apple Store 零售店信息，可供查阅

* storeInfo.py 包装了大量函数对 storeInfo.json 进行处理，这包括：

  * **_func_** `storeReturn(args, sort=True, remove_closed=False, remove_future=False, fuzzy=False, needSplit=False):`

  传入关键字，包括店号、店名、城市、国家或地区可搜索零售店，默认自动按照行政区划进行排序，还可配置启用模糊搜索、移除未开业零售店、移除已关闭零售店等。

  ```python
  >>> storeReturn("480，Los Angeles, 招聘，江浙沪", needSplit=True)
  
  [('359', '南京东路'), ('389', '浦东'), ('390', '香港广场'), ('401', '上海环贸 iapm'), ('581', '五角场'), ('678', 'Store in Shanghai'), ('683', '环球港'), ('705', '七宝'), ('761', 'Store in Shenzhen East'), ('493', '南京艾尚天地'), ('574', '无锡恒隆广场'), ('643', '虹悦城'), ('688', '苏州'), ('703', '玄武湖'), ('471', '西湖'), ('531', '天一广场'), ('532', '杭州万象城'), ('480', '解放碑'), ('756', 'Store in New Delhi'), ('744', 'Store in Mumbai'), ('760', 'Store in Seoul South'), ('050', 'The Grove'), ('108', 'Century City'), ('124', 'Beverly Center'), ('720', 'Tower Theatre'), ('755', 'Store in East Rutherford')]
  ```

  * **_func_** `stateReplace(rstores)`

  传入零售店店号数组，将按照行政区划进行压缩，便于一次性输出多个零售店。

  ```python
  >>> stateReplace(['480', '476', '573', '580', '670'])
  ['重庆 (3)', '580', '云南 (1)']
  ```
  
  * **_coro_** `storeDict(sid=None, sif=None, session=None, mode="dict")`
  
  传入零售店店号，联网从 Apple 官网获取零售店基本信息简单处理后返回。
  
  ```python
  >>> await storeDict(sid=480)
  {'latitude': 29.560981, 'longitude': 106.572272, 'timezone': 'Asia/Shanghai', 'telephone': '400-617-1224', 'address': '重庆市渝中区邹容路 108 号', 'province': '重庆, 重庆, 400010', 'isnso': False, 'regular': [{'name': 'Saturday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Wednesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Friday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Monday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Tuesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Thursday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Sunday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}], 'special': []}
  ```
  
  * **_func_** `storeInfo(sid)`
  
  传入零售店店号，不联网从本地返回基本零售店信息。
  
  ```python
  >>> storeInfo(79)
  {'name': ['銀座', '银座', 'Ginza'], 'flag': '🇯🇵', 'nso': ['2003-11-30', '2022-08-30'], 'last': '31 Aug 2022 13:40:51', 'key': {'state': '東京都', 'city': '中央区', 'alter': 'Tokyo Chuo', 'website': 'ginza'}, 'timezone': 'Asia/Tokyo'}
  ```
  
* modules/today.py 定义了 Today at Apple 的各种对象，具有丰富的属性和方法

  * 零售店对象定义了获得课程和排课方法等

  ```python
  # 零售店对象
  >>> Store(sid=480)
  <Store "解放碑" (R480), "jiefangbei", "/cn">
  ```
  
  ```python
  # 获得零售店课程
  >>> await Store(sid=480).getCourses()
  [
    <Course 6635235077318869345 "光影实验室：执导拍摄人像", "photo-lab-directing-portrait">, 
    <Course 6443623163745894793 "音乐技巧：库乐队使用入门", "music-skills-getting-started-garageband">, 
    <Course 6448288470942974313 "视频漫步：拍出电影级画面", "video-walks-capturing-cinematic-shots">, 
    <Course 6716856769744568921 "技巧：管理你的屏幕使用时间", "skills-managing-your-screen-time">
  ]
  ```
  
  ```python
  # 获得零售店排课
  >>> await Store(sid=480).getSchedules()
  [
    <Schedule 6917310504008783289 of 6444985410678260613, 4/15 17:30-18:00 @ R480>, 
    <Schedule 6917310552016813261 of 6443623163745894793, 4/15 18:00-18:30 @ R480>, 
    <Schedule 6917310598451930025 of 6716861058294579581, 4/15 19:00-20:00 @ R480>, 
    <Schedule 6918023706237569673 of 6444985410678260613, 4/15 11:00-11:30 @ R480>
  ]
  ```
  
  * 课程对象包含课程的各项属性（如课程名、封面图片 URL、介绍）等，并提供获得排课的方法
  
  ```python
  # 从 URL 获得课程，也可以手动创建课程对象
  >>> course = await parseURL("https://www.apple.com.cn/today/event/design-lab-liu-zhizhi-111922", coro=True)
  
  # 对象的字符串输出形式
  >>> course
  <Course 6978267057884660649 "设计实验室：跟着刘治治制作宣传海报探索设计奥义", "design-lab-liu-zhizhi-111922", Collection <好创意，好生意>>
  ```
  
  ```python
  # 宽屏幕宣传图
  >>> course.images["landscape"]
  'https://digitalassets-taa.cdn-apple.com/zh/cn/design-lab-liu-zhizhi-111922-wwdesign-lab-liu-zhizhi-111922-wwdesign-lab-liu-zhizhi-111922_16x9.jpg'
  ```
  
  ```python
  # 所在课程合集 Collection 对象
  >>> course.collection 
  <Collection "好创意，好生意", "creativity-for-business", "/cn">
  ```
  
  ```python
  # 课程嘉宾信息 Talent 对象
  >>> course.talents
  [<Talent 刘治治, "平面设计师">, <Talent 卷宗Wallpaper＊, "媒体">]
  
  >>> course.talents[0].description
  '毕业于中央美术学院平面设计专业，国际平面设计师联盟 (AGI) 会员，设计工作室“立入禁止”联合创始人，任教于中央美院设计学院。'
  ```
  
  ```python
  # 获得课程在某个零售店的排课
  >>> await course.getSchedules(Store(sid=320))
  [<Schedule 6978267057884660649 of 6978267057884660649, 11/19 15:00-16:30 @ R320>]
  ```
  
  * 排课对象包含每次排课的属性，并可链接对应的 `Course` 和 `Store` 对象
  
  ```python
  # 从 URL 获得课程，也可以手动创建课程对象
  >>> schedule = await parseURL("https://www.apple.com.cn/today/event/exclusive-xiong-xiaomo-110422/6986163410879022413/?sn=R320", coro=True)
  ```
  
  ```python
  >>> schedule
  <Schedule 6986163410879022413 of 6986163410879022413, 11/4 20:00-21:30 @ Online>
  
  >>> schedule.store
  <Store "三里屯" (R320), "sanlitun", "/cn">
  
  >>> schedule.course
  <Course 6986163410879022413 "独家呈献：跟着熊小默感受品牌故事的力量", "exclusive-xiong-xiaomo-110422", Collection <好创意，好生意>>
  ```
  
  ```python
  # 带有时区信息的课程时间对象
  >>> schedule.timeStart
  datetime.datetime(2022, 11, 4, 20, 0, tzinfo=zoneinfo.ZoneInfo(key='Asia/Shanghai'))
  
  # 按照预设或给定格式格式化课程时间
  >>> schedule.datetimeStart(form = "Starting %B %-d, %-I:%M %p")
  'Starting November 4, 8:00 PM'
  ```
  
  该代码中还设计了 `Talent` 对象、`Sitemap` 对象，以及将 `Course`、`Schedule` 输出为适用于 Telegram 输出的 `teleinfo` 函数。
  
* bannerMessage.py 作为一个示例

  由于在 storeInfo.py 当中已经包装了大量实用函数，假设案例是获取 Apple Store 零售店官网的提示信息（常用于特别营业时间、搬迁、临时关闭、特别活动等展示），在主函数代码中，只需要：

  * 指定要查询的零售店（通过 `storeReturn` 函数可以轻松的指定）
  * 查询所需要的信息（通过并发 `storeDict` 可以极快的速度获得信息）
  * 对结果进行格式化（通过 `storeReturn` 获得的零售店默认已经按照行政区划进行排序，还可以通过 `Order` 顺序表、`stateReplace` 拼合一个城市的多家零售店、`getCity` `getState` `getNation` `storeInfo` 获取零售店信息等）
  * 产生输出（代码最末端的 `push` 字典，可按照需求推送至 app 等）



### 结果推送

许多代码设计为可以和本地记录的信息进行比较，在有新结果时推送通知。在这些代码的顶部，可能有：

```python
from sdk_aliyun import async_post
from bot import tokens
```

这是我个人对结果推送的实现方式，`sdk_aliyun` 和 `bot` 并未在此库中给出。代码运行到输出阶段会产生一个包含文本、图片、链接等内容的字典，您可以通过编写适合您自己的推送结果的方式以获取代码结果，例如将内容推送至 Telegram Channel、微信公众号、其他第三方 iOS 推送 app 等。



## 库历史

2019 年 6 月：迁移库并命名 asaDuplex。[[commit]](https://github.com/junyilou/asaduplex/commit/e405a00ab74969a7dcacb719bdab2847e59becb8)

2019 年 8 月：完全升级 Python 3。[[commit]](https://github.com/junyilou/asaduplex/commit/a6ac48353a318586751e4a7f901c8c4d2692b26d)

2019 年 11 月：停止通过 while True 和 time.sleep 进行持续的前台运行，改为一次执行代码，引入 logging 做为输出。[[commit]](https://github.com/junyilou/asaduplex/commit/6ca8a09d112fe3a67ac1d28f53ec6446f99b83e7)

2020 年 11 月：停止通过 IFTTT Webhooks 将代码结果发至 iOS 用户，改为使用 Telegram Bot 推送结果，同时也支持了在发送的内容中应用 Markdown 文本样式、按钮、链接等。[[commit]](https://github.com/junyilou/asaduplex/commit/bd1acf74a33dcb44c2076d1aac67559b547d7a0b)

2021 年 2 月：将 specialHours (现 Hours)、Rtlimages (现 Rtl) 变得更加模块化，使数据获取和数据处理分析分开，方便其他代码可以利用相同的数据实现其他的功能。[[commit1]](https://github.com/junyilou/asaduplex/commit/f2d31a134ec074ae699c8df08ab916865d799dc4) [[commit2]](https://github.com/junyilou/asaduplex/commit/0f9157af532ae5f91831217d574099a7841ee247)

2021 年 3 月：利用 asaDuplex 中的部分代码，推出果铺知道 Telegram Bot，方便用户快速查询 Apple Store 零售店信息及特别营业时间信息。

2021 年 8 月：进一步模块化代码，并将代码结果推送剥离，不再依赖 Telegram Bot 做结果推送。[[commit]](https://github.com/junyilou/asaduplex/commit/9537444cadaf4b6b989ff26f3b2313f3aaf8c17c)

2022 年 3 月：使用 asyncio、aiohttp 异步化核心代码，极大幅度的提高运行速度。[[commit]](https://github.com/junyilou/asaduplex/commit/6c7e3b729ab1ced4a8ae8888a5930fc55df8319e)

2022 年 4 月：使用面向对象的思想，极高的提升了 Today at Apple 对象的多样性。[[commit]](https://github.com/junyilou/asaduplex/commit/4d98ae7f00312630479243184e715c929afd5b7a)

2022 年 10 月：改进代码使用 Python 3.8 [[commit]](https://github.com/junyilou/asaduplex/commit/2e7511ed22c38b7272f5b3e041ed6d66f8dcf21c)、Python 3.9 [[commit]](https://github.com/junyilou/asaduplex/commit/dcfa943e543c157ca14a7e14cf98c98732ffc400)、Python 3.10 [[commit]](https://github.com/junyilou/asaduplex/commit/78543f98a8c22b3aa6b93d6bc14d76b5f217e027)、Python 3.11 的部分特性。



## 底注

免责声明：

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。以上代码中的数据，包括但不限于 storeInfo.json、storeList.json，均来自公开的 Apple 官方网站及其其它服务器。未经特别注明内容均有其版权。未经特别授权，所涉及到的任何文本、图片应仅作个人兴趣用途。有关更多 Apple 商标和内容使用细则，请参见 Apple Legal 及其 Intellectual Property 页面。

Disclaimer:

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. All data used in the code, including but not limited to 'storeInfo.json', 'storeList.json', were from Apple's official websites or its other public servers. Unless otherwise indicated, all materials are copyrighted. No part, unless explicit authorization, either text or images may be used for any purpose other than personal interests. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its Intellectual Property webpages.