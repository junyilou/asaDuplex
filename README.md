### asaDuplex

**一个完全关于 Apple Store 的 Repository。** — Junyi

果铺知道通过以下代码获得了许多关于 Apple Store 零售店的信息更新，

你可以在[微博](https://weibo.com/arsteller)和 [Telegram Channel](https://t.me/guopuzd) 关注果铺知道以直接接收以下代码的运行结果。

\-

### 大事记

2019 年 8 月：所有代码要求使用 Python 3，不向下兼容 Python 2。

2019 年 11 月：起初，这些代码大多通过 while True 和 time.sleep 自带计划任务，现在改为一次执行代码，推荐配合 crontab 等计划任务命令使用。代码中引入了 logging 来保存代码的运行 log。

2020 年 11 月：起初，这些代码配合 IFTTT Webhooks 将代码结果发至 iOS 用户，但 IFTTT 不愿意开放三个以上的参数，且在 2020 年末开始实行 IFTTT Pro 会员制，现在改为使用 Telegram Bot 推送结果，同时也支持了在发送的内容中应用 Markdown 文本样式、按钮、链接等。

\-

Telegram Bot 推送部分使用了 [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) 库，你需要首先安装此库。

要正确接收代码结果，还需首先在同目录创建名为 bot.py 的文件，包含至少一个 Bot Token 和接收消息的 Chat ID（可以是一个用户、Channel 等），一个示例是：

```python
# bot.py
tokens = ["1234567890:ABCDEFghijklMNOPQRstu_vwxY-Z0123456"] # Bot Token
chat_ids = ["123456789", "-1024204840964"] # 通常一个用户是正数，Channel 是负数
```

在下述代码的顶部都有导入 bot.py 的代码，选择其中一个 Bot Token 和 chat_id 继续。当然也可以选择直接把 token 和 chat_id 直接写在对应代码中，这里使用 bot.py 是为了方便 Git 管理。

 \-

### 代码

* allStoresInfoLite.py: 从 mobileapps.apple.com 刷新 Apple Store 零售店信息
* Recruitment.py: 获得正在招聘的 Apple Store 零售店以观察新店招聘情况
* Rtlimages.py: 获得 Apple 服务器中每一零售店图片的最后修改时间并与已知比较判定新图
* specialHours.py: 获得 Apple Store 零售店的特别营业时间动态更新
* storeDistance.py: 通过 storeList.json 中的坐标计算全球零售店距离
* Today.py: 取得中国最新 Today at Apple 活动

### 已移除的代码

* inStock.py: 根据产品部件号码查寻指定产品在指定零售店的库存情况，为避免滥用移除
* onlineCrawl.py: 通过访问 Apple 官网以寻找新上架的产品部件号码，为避免滥用移除
* IFTTT.py: 起初为了 IFTTT Webhooks 推送创建的辅助程序，现已不再需要

### 文本文档

* savedEvent.txt: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* storeInfo.json: 全球 Apple Store 名称、店号、所属地旗帜和已知图片的最后修改时间
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的结果

\-

###### 底注

免责声明：

果铺知道是完全个人性质的微博账户和 Telegram Channel，果铺知道不受美国苹果公司授权、许可或赞助。以上代码中的数据均来自公开的 Apple 官方网站及其其它服务器。未经特别注明内容均有其版权。未经特别授权，所涉及到的任何文本、图片应仅作个人兴趣用途使用。有关更多 Apple 商标和内容使用细则，请参见 Apple Legal 及其 Intellectual Property 页面。

Disclaimer:

果铺知道, or 'Guo Pu Zhi Dao' is a completely personal-background Weibo Account and Telegram Channel. Guo Pu Zhi Dao is in no way authorized, approved, or endorsed by Apple, Inc. All data used in the code were from Apple's official websites or its other public servers. Unless otherwise indicated, all materials are copyrighted. No part, unless explicit authorization, either text or images may be used for any purpose other than personal interests use. For further information about policies on using Apple's trademarks and contents, please visit Apple Legal and its Intellectual Property page.