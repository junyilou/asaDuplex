### asaDuplex

![bot](Retail/bot.jpg)

\* asaDuplex 尚不开源 Telegram Bot 的运行代码，您可以在[这里](https://t.me/guopuzdbot)进行体验。

## 仓库内容

#### 代码

* allStoresInfoLite.py: 取得 Apple Store 零售店服务器信息
* Recruitment.py: 取得全球 Specialist 招聘情况以获得未来新店
* Rtl.py: 取得 Apple Store 零售店服务器图片更新
* Hours.py: 取得 Apple Store 特别营业时间信息
* Today.py 和 Sitemap.py: 取得最新 Today at Apple 活动

#### 模块

* storeInfo.py: 处理 storeInfo.json 的数据，提供强大的通用函数

* modules/special.py: 分析 Apple Store 零售店营业时间，并尝试获得特别营业时间内部备忘录
* modules/constants.py: 保存部分常量和通用函数

#### 文本

* savedEvent.txt、savedSitemap: 由 Today.py 或 Sitemap.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedJobs.txt: 由 Recruitment.py 生成的，已经在检测到招聘的零售店编号
* storeInfo.json: 全球 Apple Store 名称（包含部分曾用名、ASCII 兼容名等以便于更广的匹配）、店号、国家或地区旗帜、开店时间、官网图片最后修改时间、URL 标签、全球各国地区零售店按行政区划字典、用于模糊搜索的关键字 alias 等
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的零售店详细信息

## 您可以如何使用本库分享的数据

* storeInfo.json 提供了极为丰富的 Apple Store 零售店信息，可供查阅

* storeInfo.py 包装了大量函数对 storeInfo.json 进行处理，这包括：

  * `storeReturn(args, sort = True, remove_close = False, remove_future = False, fuzzy = False, no_country = False)`

  传入关键字，包括店号、店名、城市、国家或地区可搜索零售店，默认自动按照行政区划进行排序，还可配置启用模糊搜索、移除未开业零售店、移除已关闭零售店等。

  ```python
  >>> storeReturn("浙江 南京 🇲🇴 670")
  
  [('493', '南京艾尚天地'), ('643', '虹悦城'), ('703', '玄武湖'), ('670', '昆明'), ('471', '西湖'), ('531', '天一广场'), ('532', '杭州万象城'), ('672', '澳門銀河'), ('697', '路氹金光大道')]
  ```

  * `stateReplace(rstores)`

  传入零售店店号数组，将按照行政区划进行压缩，便于一次性输出多个零售店。

  ```python
  >>> stateReplace(['480', '476', '573', '580', '670'])
  
  ['重庆 (3)', '580', '云南 (1)']
  ```

  * `storeDict(storeid, mode = "dict")`

  传入零售店店号，联网从 Apple 官网获取零售店基本信息简单处理后返回。

  ```python
  >>> storeDict(480)
  
  {'latitude': 29.560981, 'longitude': 106.572272, 'timezone': 'Asia/Shanghai', 'telephone': '400-617-1224', 'address': '重庆市渝中区邹容路 108 号', 'province': '重庆, 重庆, 400010', 'regular': [{'name': 'Monday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Tuesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Wednesday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Thursday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Friday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Saturday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}, {'name': 'Sunday', 'openTime': '10:00', 'closeTime': '22:00', 'closed': False}], 'special': []}
  ```

  * `storeInfo(storeid)`

  传入零售店店号，不联网从本地返回基本零售店信息。

  ```python
  >>> storeInfo(480)
  
  {'name': ['解放碑', 'Jiefangbei'], 'flag': '🇨🇳', 'nso': '2015-1-31', 'last': '29 Aug 2021 06:57:49', 'website': 'jiefangbei'}
  ```

* Hours、Today 等代码设计为可以比较本地已经保存的结果（例如已经记录的 Today at Apple 活动）寻找差异并输出图文结果，这些数据也被用到了果铺知道 Bot 和果铺知道 Channel 中。

  ![today](Retail/today.jpg)

  在许多代码的顶部，可能包含类似如下代码：

  ```python
  from sdk_aliyun import post
  from bot import tokens
  ```

  这是我个人对结果推送的实现方式，`sdk_aliyun` 和 `bot` 并未在此库中给出。

  可以看到，代码运行到输出阶段会产生一个包含文本、图片、链接等内容的字典，您可以通过编写适合您自己的推送结果的方式以获取代码结果，例如将内容推送至 Telegram Channel、微信公众号、其他第三方 iOS 推送 app 等。

## 库历史

2019 年 8 月：迁移库并命名 asaDuplex，所有代码要求使用 Python 3。

2019 年 11 月：停止通过 while True 和 time.sleep 进行持续的前台运行，改为一次执行代码，引入 logging 做为输出。

2020 年 11 月：停止通过 IFTTT Webhooks 将代码结果发至 iOS 用户，改为使用 Telegram Bot 推送结果，同时也支持了在发送的内容中应用 Markdown 文本样式、按钮、链接等。

2021 年 2 月：将 specialHours (现 Hours)、Rtlimages (现 Rtl) 变得更加模块化，使数据获取和数据处理分析分开，方便其他代码可以利用相同的数据实现其他的功能。

2021 年 3 月：利用 asaDuplex 中的部分代码，推出果铺知道 Telegram Bot，方便用户快速查询 Apple Store 零售店信息及特别营业时间信息。

2021 年 8 月：进一步模块化代码，并将代码结果推送剥离，不再依赖 Telegram Bot 做结果推送。

## ~~已移除的代码~~

* inStock.py: 根据产品部件号码查寻指定产品在指定零售店的库存情况，为避免滥用移除
* onlineCrawl.py: 通过访问 Apple 官网以寻找新上架的产品部件号码，为避免滥用移除
* IFTTT.py: 起初为了 IFTTT Webhooks 推送创建的辅助程序，现已不再需要

## 底注

免责声明：

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。以上代码中的数据，包括但不限于 storeInfo.json、storeList.json，均来自公开的 Apple 官方网站及其其它服务器。未经特别注明内容均有其版权。未经特别授权，所涉及到的任何文本、图片应仅作个人兴趣用途。有关更多 Apple 商标和内容使用细则，请参见 Apple Legal 及其 Intellectual Property 页面。

Disclaimer:

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. All data used in the code, including but not limited to 'storeInfo.json', 'storeList.json', were from Apple's official websites or its other public servers. Unless otherwise indicated, all materials are copyrighted. No part, unless explicit authorization, either text or images may be used for any purpose other than personal interests. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its Intellectual Property webpages.