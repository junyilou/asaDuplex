### asaDuplex

![bot](Retail/bot.jpg)

\* asaDuplex 尚不开源 Telegram Bot 的运行代码，您可以在[这里](https://t.me/guopuzdbot)进行体验。

## 仓库内容

#### 代码

* allStoresInfoLite.py: 取得 Apple Store 零售店服务器信息
* Recruitment.py: 取得全球 Specialist 招聘情况以获得未来新店
* Rtl.py: 取得 Apple Store 零售店服务器图片更新
* Hours.py: 取得 Apple Store 特别营业时间信息
* Today.py: 取得最新 Today at Apple 活动

#### 模块

* storeInfo.py: 处理 storeInfo.json 的数据，提供强大的通用函数
* modules/special.py: 分析 Apple Store 零售店营业时间，并尝试获得特别营业时间内部备忘录
* modules/today.py: 一个定义了 Today at Apple 课程、排课、零售店对象的模块
* modules/constants.py: 保存部分常量和通用函数

#### 文本

* savedEvent.json: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedJobs.txt: 由 Recruitment.py 生成的，已经在检测到招聘的零售店编号
* storeInfo.json: 全球 Apple Store 名称（包含部分曾用名、ASCII 兼容名等以便于更广的匹配）、店号、国家或地区旗帜、开店时间、官网图片最后修改时间、URL 标签、全球各国地区零售店按行政区划字典、用于模糊搜索的关键字 alias 等
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的零售店详细信息

#### 代码依赖

本代码的网络 I/O 请求依赖 [requests](https://github.com/psf/requests)、[aiohttp](https://github.com/aio-libs/aiohttp)，为了分析 Today at Apple 活动所在地区的时区信息，依赖 pytz，可通过 pip 安装

## 如何使用

* storeInfo.json 提供了极为丰富的 Apple Store 零售店信息，可供查阅

* storeInfo.py 包装了大量函数对 storeInfo.json 进行处理，这包括：

  * function `storeReturn(args, sort = True, remove_closed = False, remove_future = False, fuzzy = False, needSplit = False):`

  传入关键字，包括店号、店名、城市、国家或地区可搜索零售店，默认自动按照行政区划进行排序，还可配置启用模糊搜索、移除未开业零售店、移除已关闭零售店等。

  ```python
  >>> storeReturn("480，Los Angeles, 招聘，江浙沪", needSplit = True)
  
  [('359', '南京东路'), ('389', '浦东'), ('390', '香港广场'), ('401', '上海环贸 iapm'), ('581', '五角场'), ('678', 'Store in Shanghai'), ('683', '环球港'), ('705', '七宝'), ('493', '南京艾尚天地'), ('574', '无锡恒隆广场'), ('643', '虹悦城'), ('688', '苏州'), ('703', '玄武湖'), ('471', '西湖'), ('531', '天一广场'), ('532', '杭州万象城'), ('575', 'Store in Wuhan'), ('480', '解放碑'), ('329', 'Store in London'), ('756', 'Store in New Delhi'), ('744', 'Store in Mumbai'), ('738', 'Store in Seoul'), ('751', 'Store in Seoul East'), ('050', 'The Grove'), ('108', 'Century City'), ('124', 'Beverly Center'), ('720', 'Tower Theatre')]
  ```

  * function `stateReplace(rstores)`

  传入零售店店号数组，将按照行政区划进行压缩，便于一次性输出多个零售店。

  ```python
  >>> stateReplace(['480', '476', '573', '580', '670'])
  
  ['重庆 (3)', '580', '云南 (1)']
  ```

  * coroutine `storeDict(session, storeid, mode = "dict", sif = None)`

  传入零售店店号，联网从 Apple 官网获取零售店基本信息简单处理后返回。

  ```python
  >>> async with aiohttp.ClientSession() as session:
  ...     await storeDict(session, 480)
  
  {'latitude': 29.560981, 'longitude': 106.572272, 'timezone': 'Asia/Shanghai', 'telephone': '400-617-1224', 'address': '重庆市渝中区邹容路 108 号', 'province': '重庆, 重庆, 400010', 'isnso': False, 'regular': [{'name': 'Saturday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Wednesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Friday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Monday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Tuesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Thursday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Sunday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}], 'special': []}
  ```

  * function `storeInfo(storeid)`

  传入零售店店号，不联网从本地返回基本零售店信息。

  ```python
  >>> storeInfo(580)
  
  {'name': ['成都太古里', 'Taikoo Li Chengdu'], 'flag': '🇨🇳', 'nso': '2015-11-21', 'last': '07 Jan 2022 08:59:07', 'website': 'taikoolichengdu', 'key': {'state': '四川', 'city': '成都', 'alter': 'Sichuan Chengdu'}}
  ```

* today.py 定义了 Today at Apple 的对象，每个课程、排课均为一个 `class`，具有丰富的属性和方法

  * 零售店对象定义了获得课程和排课方法等

  ```python
  # 零售店对象
  >>> Store(sid = 480)
  <Store "解放碑" (R480), "jiefangbei", "/cn">
  
  # 获得零售店课程
  >>> await Store(sid = 480).getCourses()
  [
    <Course 6635235077318869345 "光影实验室：执导拍摄人像", "photo-lab-directing-portrait">, 
    <Course 6443623163745894793 "音乐技巧：库乐队使用入门", "music-skills-getting-started-garageband">, 
    <Course 6448288470942974313 "视频漫步：拍出电影级画面", "video-walks-capturing-cinematic-shots">, 
    <Course 6716856769744568921 "技巧：管理你的屏幕使用时间", "skills-managing-your-screen-time">
  ]
  
  # 获得零售店排课
  >>> await Store(sid = 480).getSchedules()
  [
    <Schedule 6917310504008783289 of 6444985410678260613, 4 月 15 日 17:30 to 18:00:00, at R480>, 
    <Schedule 6917310552016813261 of 6443623163745894793, 4 月 15 日 18:00 to 18:30:00, at R480>, 
    <Schedule 6917310598451930025 of 6716861058294579581, 4 月 15 日 19:00 to 20:00:00, at R480>, 
    <Schedule 6918023706237569673 of 6444985410678260613, 4 月 16 日 11:00 to 11:30:00, at R480>
  ]
  ```
  
  * 课程对象包含课程的各项属性（如课程名、封面图片 URL、介绍）等，并提供获得排课的方法
  
  ```python
  # 从 URL 获得课程，也可以手动创建课程对象
  >>> course = await parseURL("https://www.apple.com.cn/today/event/photo-lab-directing-portrait/", coro = True)
  
  >>> course
  <Course 6635235077318869345 "光影实验室：执导拍摄人像", "photo-lab-directing-portrait">
  
  >>> course.images
  {
    'portrait': 'https://digitalassets-taa.cdn-apple.com/prod/image/photo-lab-directing-portrait-ww/2020-03/29a29970-2a6c-49e3-9fb4-8b146f3df6f8__4x5.jpg', 
    'landscape': 'https://digitalassets-taa.cdn-apple.com/prod/image/photo-lab-directing-portrait-ww/2020-03/09bc55d1-0a62-4eed-8cd5-3f4511e857ab__16x9.jpg'
  }
  
  >>> course.getSchedules(Store(sid = 480))
  [
    <Schedule 6918024654175448253 of 6635235077318869345, 4 月 17 日 14:00 to 15:00:00, at R480>, 
    <Schedule 6918027046157664333 of 6635235077318869345, 4 月 22 日 14:00 to 15:00:00, at R480>, 
    <Schedule 6918027087207317837 of 6635235077318869345, 4 月 22 日 16:00 to 17:00:00, at R480>
  ]
  ```
  
  * 排课对象包含每次排课的属性，包括所在零售店（`Store` 对象）、所属课程（`Course` 对象），开始和结束时间等
  
  ```python
  # 从 URL 获得课程，也可以手动创建课程对象
  >>> schedule = await parseURL("https://www.apple.com.cn/today/event/photo-lab-directing-portrait/6911594146335944905/?sn=R645", coro = True)
  
  >>> schedule
  <Schedule 6911594146335944905 of 6635235077318869345, 4 月 18 日 18:30 to 19:30:00, at R645>
  
  >>> schedule.course
  <Course 6635235077318869345 "光影实验室：执导拍摄人像", "photo-lab-directing-portrait">
  
  >>> schedule.timeStart
  datetime.datetime(2022, 4, 18, 18, 30, tzinfo=<DstTzInfo 'Asia/Shanghai' CST+8:00:00 STD>)
  
  >>> schedule.url
  'https://www.apple.com.cn/today/event/photo-lab-directing-portrait/6911594146335944905/?sn=R645'
  ```
  
  此外，还提供了将 `Course` 和 `Schedule` 对象的信息进行提取，并综合至一条 Telegram 消息中的函数（效果如下图）；分析 Today at Apple 网站地图 XML Sitemap 的 `Sitemap` 对象等。
  
  此模块中，涉及到网络请求的函数均适用 aiohttp 的异步 I/O，故部分对象初始化和方法调用需要使用 `await` 关键字；代码中，也提供了异步转同步方法 `sync()`，方便在复杂度不高的代码中同步使用。网络请求使用线程池从而无需用户手动创建网络请求线程。
  
* Hours.py、Today.py 等代码设计为可以比较本地已经保存的结果（例如已经记录的 Today at Apple 活动）寻找差异并输出图文结果，这些数据也被用到了果铺知道 Bot 和果铺知道 Channel 中。

  ![today](Retail/today.jpg)

  在代码的顶部，可能包含类似如下代码：

  ```python
  from sdk_aliyun import async_post
  from bot import tokens
  ```

  这是我个人对结果推送的实现方式，`sdk_aliyun` 和 `bot` 并未在此库中给出。代码运行到输出阶段会产生一个包含文本、图片、链接等内容的字典，您可以通过编写适合您自己的推送结果的方式以获取代码结果，例如将内容推送至 Telegram Channel、微信公众号、其他第三方 iOS 推送 app 等。

## 库历史

2019 年 8 月：迁移库并命名 asaDuplex，所有代码要求使用 Python 3。

2019 年 11 月：停止通过 while True 和 time.sleep 进行持续的前台运行，改为一次执行代码，引入 logging 做为输出。

2020 年 11 月：停止通过 IFTTT Webhooks 将代码结果发至 iOS 用户，改为使用 Telegram Bot 推送结果，同时也支持了在发送的内容中应用 Markdown 文本样式、按钮、链接等。

2021 年 2 月：将 specialHours (现 Hours)、Rtlimages (现 Rtl) 变得更加模块化，使数据获取和数据处理分析分开，方便其他代码可以利用相同的数据实现其他的功能。

2021 年 3 月：利用 asaDuplex 中的部分代码，推出果铺知道 Telegram Bot，方便用户快速查询 Apple Store 零售店信息及特别营业时间信息。

2021 年 8 月：进一步模块化代码，并将代码结果推送剥离，不再依赖 Telegram Bot 做结果推送。

2022 年 3 月：使用 asyncio、aiohttp 异步化核心代码，极大幅度的提高运行速度。

2022 年 4 月：使用面向对象的思想，极高的提升了 Today at Apple 对象的多样性

## ~~已移除的代码~~

* inStock.py: 根据产品部件号码查寻指定产品在指定零售店的库存情况，为避免滥用移除
* onlineCrawl.py: 通过访问 Apple 官网以寻找新上架的产品部件号码，为避免滥用移除
* IFTTT.py: 起初为了 IFTTT Webhooks 推送创建的辅助程序，现已不再需要

## 底注

免责声明：

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。以上代码中的数据，包括但不限于 storeInfo.json、storeList.json，均来自公开的 Apple 官方网站及其其它服务器。未经特别注明内容均有其版权。未经特别授权，所涉及到的任何文本、图片应仅作个人兴趣用途。有关更多 Apple 商标和内容使用细则，请参见 Apple Legal 及其 Intellectual Property 页面。

Disclaimer:

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. All data used in the code, including but not limited to 'storeInfo.json', 'storeList.json', were from Apple's official websites or its other public servers. Unless otherwise indicated, all materials are copyrighted. No part, unless explicit authorization, either text or images may be used for any purpose other than personal interests. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its Intellectual Property webpages.