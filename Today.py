import os, json, time, logging, IFTTT
from retailData import filename, storename

rpath, wAns, allChina = os.path.expanduser('~') + "/Retail/", "", len(filename)
with open(rpath + "savedEvent.txt") as m: mark = m.read()

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')
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