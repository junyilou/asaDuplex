import os, json, time, logging
import IFTTT

filename = ['qibao', 'shanghaiiapm', 'wujiaochang', 'nanjingeast', 'pudong', 'globalharbor','hongkongplaza', 'kunming', 
'sanlitun', 'chinacentralmall', 'chaoyangjoycity', 'wangfujing', 'xidanjoycity', 'mixcchengdu', 'taikoolichengdu', 'tianjinjoycity','riverside66tianjin',
'mixctianjin', 'parc66jinan', 'mixcqingdao', 'parccentral','zhujiangnewtown', 'holidayplazashenzhen', 'mixcnanning', 'nanjingist', 'nanjingjinmaoplace', 
'wondercity', 'center66wuxi', 'suzhou', 'mixczhengzhou', 'tianyisquare', 'mixchangzhou', 'westlake', 'xiamenlifestylecenter', 'tahoeplaza', 
'olympia66dalian', 'parkland', 'zhongjiejoycity', 'mixcshenyang', 'jiefangbei', 'mixcchongqing', 'paradisewalkchongqing']

storename = ['七宝', '上海环贸 iapm', '五角场', '南京东路', '浦东', '环球港', '香港广场', '昆明', 
'三里屯', '华贸购物中心', '朝阳大悦城', '王府井', '西单大悦城', '成都万象城', '成都太古里', '天津大悦城', '天津恒隆广场', 
'天津万象城', '济南恒隆广场', '青岛万象城', '天环广场', '珠江新城', '深圳益田假日广场', '南宁万象城', '南京艾尚天地', '南京金茂汇', 
'虹悦城', '无锡恒隆广场', '苏州', '郑州万象城', '天一广场', '杭州万象城', '西湖', '厦门新城市广场', '泰禾广场', 
'大连恒隆广场', '百年城', '中街大悦城', '沈阳万象城', '解放碑', '重庆万象城', '重庆北城天街']

rpath, wAns = os.path.expanduser('~') + "/Retail/", ""
with open(rpath + "savedEvent.txt") as m: mark = m.read()

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, datefmt = '%T')
logging.info("程序启动")

for fn in filename:
	logging.info("正在下载活动时间表文件: " + fn)
	os.system("wget -t 20 -T 3 -O " + rpath + fn + ".json --no-check-certificate " +
		"'https://www.apple.com/today-bff/landing/store?stageRootPath=/cn&storeSlug=" + fn + "'")

for fn, cyn in zip(filename, storename):
	with open(rpath + fn + ".json") as r:
		raw = r.read(); rJson = json.loads(raw.replace("\u2060", ""))["courses"]
	for rTitle in rJson:
		rCourse = rJson[rTitle]; singleName = rCourse["name"]
		if not singleName in mark and not singleName in wAns: 
			logging.info("在 Apple " + cyn + " 找到了新活动: " + singleName)
			wAns += singleName + ",\n"; citAns = cyn
			for sn, csn in zip(filename, storename):
				logging.info("正在寻找 Apple " + csn + " 有没有相同的活动")
				with open(rpath + sn + ".json") as e: 
					eAns = e.read()
					eJson = json.loads(eAns.replace("\u2060", ""))["courses"]
				for eTitle in eJson:
					eCourse = eJson[eTitle]
					if eCourse["name"] == singleName and not csn in citAns:
						logging.info("找到 Apple " + csn + " 有相同的活动")
						citAns += "、" + csn
			pushAns = "#TodayatApple " + citAns + "有新活动: " + singleName
			pushAns = pushAns.replace('"', "").replace("'", "").replace("：", " - ")
			logging.info("[运行结果] " + pushAns)
			pictureURL = rCourse["backgroundMedia"]["images"][0]["landscape"]["source"]
			IFTTT.pushbots(pushAns, "Today at Apple 新活动", pictureURL, "raw", IFTTT.getkey()[0], 0)
if wAns != "":
	logging.info("正在更新 savedEvent 文件")
	with open(rpath + "savedEvent.txt", "w") as m:
		m.write(mark + wAns)

for rm in filename: os.system("rm " + rpath + rm + ".json")
logging.info("程序结束")