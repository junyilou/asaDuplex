#### 这是一个私有代码库

所有 Python 代码要求使用 Python 3, 并不向下兼容 Python 2

起初，这些代码大多通过 while True 和 time.sleep 自带计划任务，但现在正在逐渐改为一次执行代码，并要求用户在服务器配合 crontab 等计划命令使用。

### 模块
* IFTTT.py
    *  通过 key.txt 获得 API Key
    *  最大支持 3 个自定义参数推送
    *  Debug Mode 供查错和修正
* PID.py
    *  通过保存在 pid.txt 中的 PID 检查进程是否退出
    *  只需一行代码即可在其他代码中自动添加当前进程
    *  在监测到进程已经退出后自动推送通知给用户

* retailData.py 是 Recruitment.py 和 Today.py 的依赖文件

### Code
* onlineCrawl.py: 刷新 Apple Online Store 新上架的 Apple 自家产品
* Recruitment.py: 刷新全球招聘 Specialist 职位的新零售店
* Rtlimages.py: 从 rtlimages.apple.com 刷新最新 Apple Store 零售店图片
* allStoresInfoLite.py: 从 mobileapps.apple.com 刷新 Apple Store 零售店信息
* storeDistance.py: 通过 storeList.json 中的坐标计算全球零售店距离并排序
* Today.py: 取得中国内地最新 Today at Apple 活动数据
* specialHours: 获得中国内地零售店的特别营业时间动态更新


### Text
* savedEvent.txt: 由 Today.py 生成的，已经检测到并保存的 Today at Apple 活动列表
* savedProduct.txt: 由 onlineCrawl.py 生成的，从 MT 开始的已知产品部件号列表
* storeInfo.json: Apple Store 名称、ID 和所属国家或区域 emoji 旗帜
* storeList.json 和 storeList-format.json: 由 allStoresInfoLite.py 获得的结果