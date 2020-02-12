#### 内容均为兴趣作品，严禁用于商业用途

所有代码要求使用 Python 3, 并不向下兼容 Python 2。起初，这些代码大多通过 while True 和 time.sleep 自带计划任务，但现在均改为一次执行代码，并要求用户在服务器配合 crontab 等计划命令使用。

果铺知道通过以下代码获得了 Apple Store 零售店的很多动态信息更新，你可以在新浪微博和 Telegram Channel 搜索并关注果铺知道。

### 模块
* IFTTT.py
  
    用户通过在 IFTTT 网站设置 Maker Webhooks，方便代码将结果直接推送至手机 app
    
    *  通过 ~/key.txt 获得 API Key
    *  3 个自定义参数推送 (IFTTT 定的)
    *  Debug Mode 供查错和修正


### 代码
* allStoresInfoLite.py: 从 mobileapps.apple.com 刷新 Apple Store 零售店信息
* onlineCrawl.py: 获得 Apple Online Store 最新上架的 Apple 品牌产品
* Recruitment.py: 获得全球正在招聘的 Apple Store 零售店以观察新店招聘情况
* Rtlimages.py: 从 rtlimages.apple.com 获得最新的 Apple Store 零售店图片
* specialHours.py: 获得中国内地零售店的特别营业时间动态更新
* storeDistance.py: 通过 storeList.json 中的坐标计算全球零售店距离并排序
* Today.py: 取得中国内地最新 Today at Apple 活动标题

### 文本

* retailData.py: 为了避免在代码中出现大量已知数据而提前预存的一些零售店信息
* savedEvent.txt: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedProduct.txt: 由 onlineCrawl.py 生成的，从 MT 开始的已知产品部件号列表
* storeInfo.json: 部分 Apple Store 名称、店号和所属国家或区域 emoji 旗帜
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的结果



###### 果铺知道是个人性质的微博、Telegram 账户，果铺知道不受美国苹果公司赞助或授权。代码中的数据均来自公开的 Apple 官方网站及其其它服务器，未经特别注明，所涉及到的文本和媒体信息版权归原作者所有。