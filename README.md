### asaDuplex

**一个完全关于 Apple Store 的 Repository。** — Junyi

果铺知道通过以下代码获得了许多关于 Apple Store 零售店的信息，

你可以在[微博](https://weibo.com/arsteller)和 [Telegram Channel](https://t.me/guopuzd) 关注果铺知道以直接接收以下代码的运行结果。

\-

### 大事记

2019 年 8 月：所有代码要求使用 Python 3，不向下兼容 Python 2。

2019 年 11 月：停止通过 while True 和 time.sleep 实行占用内存的持久运行，改为一次执行代码，推荐配合 crontab 等计划任务命令使用。代码中引入了 logging 来保存代码的运行 log。

2020 年 11 月：停止通过 IFTTT Webhooks 将代码结果发至 iOS 用户，改为使用 Telegram Bot 推送结果，同时也支持了在发送的内容中应用 Markdown 文本样式、按钮、链接等。

2021 年 2 月：将 specialHours、Rtlimages 变得更加模块化，使数据获取和数据处理分析分开，方便其他代码可以利用相同的数据实现其他的功能。

2021 年 3 月：利用 asaDuplex 中的部分代码，推出果铺知道 Telegram Bot，方便用户快速查询 Apple Store 零售店信息及特别营业时间信息。

![bot](Retail/bot.jpg)

\-

asaDuplex 大量使用了 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 库，你需要首先安装此库。

要正确接收输出型代码的结果（通常以大写字母开头），建议首先 clone 整个库，以避免运行时缺少必要文件。同时，**需首先在同目录创建名为 bot.py 的文件**以填写结果输出对象，包含至少一个 Bot Token 和接收消息的 Chat ID（可以是一个用户、Channel 等），一个示例是：

```python
# bot.py
tokens = ["1234567890:ABCDEFghijklMNOPQRstu_vwxY-Z0123456"] # Bot Token
chat_ids = ["123456789", "-1024204840964"] # 通常一个用户是正数，Channel 是负数
```

在代码的顶部都有导入 bot.py 的代码，选择其中一个 Bot Token 和 chat_id 继续。当然你也可以选择把 token 和 chat_id 直接写在对应代码中而不是去导入，这里使用 bot.py 是为了方便 Git 管理。

\* asaDuplex 尚不开源 Telegram Bot 的运行代码。

 \-

### 代码

* allStoresInfoLite.py: 取得 Apple Store 零售店服务器信息
* Recruitment.py: 取得全球 Specialist 招聘情况以获得未来新店
* Rtl.py: 取得 Apple Store 零售店服务器图片更新
* Hours.py: 取得 Apple Store 特别营业时间信息
* Today.py: 取得最新 Today at Apple 活动
* Sitemap.py: 作为 Today.py 的补充，通过 sitemap.xml 取得额外的 Today at Apple 活动

### 数据获取模块

* storeInfo.py

  * 是一个非常强大的模块（确信），其本质是通过分析 storeInfo.json 来处理 Apple Store 零售店信息
  * StoreID, StoreName, StoreNation：可以通过输入店号、店名返回一家店的信息，在用户只记得两者之一时获得另一者；也可以通过输入 Emoji 来代表该地区所有 Apple Store 零售店
  * storeInfo：整理某店的店号、店名、国家或地区、开业时间、照片标签、官网 URL 后缀
  * storeURL：通过 URL 后缀和国家地区代码生成完整的 Apple 官网地址
  * storePage：访问由 storeURL 生成的地址，获得零售店坐标、时区、电话、地址、所在地区行政区划信息等
  * storeState：返回一个字符串，包括一个国家或地区按行政区划分类的所有 Apple Store 零售店的名字和店号
  * storePairs：自动将输入 str 分类为店号、店名、国家或地区 Emoji，例如 "🇨🇳、480、解放碑" 将返回一个字典 {"n": ["解放碑"], "r": ["480"], "s": ["🇨🇳"]}
  * storeReturn：利用一个包括 "n", "r", "s" 的字典，调用 StoreID, StoreName 和 StoreNation，找到输入对应的实际零售店，例如上面 storePairs 的例子将返回出 42 家零售店，支持定义接受的类型（例如不接受国家），支持自动按照行政区划将所有零售店排序
  * DieterInfo 类似 storeInfo 返回一个零售店的信息（店名、店号、开业时间）简述
  * DieterHeader 通过 HEAD 确认 Apple 服务器某家零售店图片的最后修改时间
  
* special.py
  * 自动解析 apple.com 源代码中提供的零售店常规营业时间安排和特别营业时间
  * 可仅返回常规营业时间数据，也可返回每个特别营业时间及其对应常规营业时间的数据
  * 已经于 2021 年 2 月底适配了新版 Apple 零售店页面 HTML 代码


### 数据文本

* savedEvent.txt: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedJobs.txt: 由 Recruitment.py 生成的，已经在检测到招聘的零售店编号
* storeInfo.json: 全球 Apple Store 名称（包含部分曾用名、ASCII 兼容名等以便于更广的匹配）、店号、国家或地区旗帜、官网图片最后修改时间、URL
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的结果

### ~~已移除的代码~~

* inStock.py: 根据产品部件号码查寻指定产品在指定零售店的库存情况，为避免滥用移除
* onlineCrawl.py: 通过访问 Apple 官网以寻找新上架的产品部件号码，为避免滥用移除
* IFTTT.py: 起初为了 IFTTT Webhooks 推送创建的辅助程序，现已不再需要

\-

###### 底注

免责声明：

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。以上代码中的数据，包括但不限于 storeInfo.json、storeList.json，均来自公开的 Apple 官方网站及其其它服务器。未经特别注明内容均有其版权。未经特别授权，所涉及到的任何文本、图片应仅作个人兴趣用途。有关更多 Apple 商标和内容使用细则，请参见 Apple Legal 及其 Intellectual Property 页面。

Disclaimer:

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. All data used in the code, including but not limited to 'storeInfo.json', 'storeList.json', were from Apple's official websites or its other public servers. Unless otherwise indicated, all materials are copyrighted. No part, unless explicit authorization, either text or images may be used for any purpose other than personal interests. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its Intellectual Property webpages.