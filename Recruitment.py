import os, json, time, logging, IFTTT
from retailData import stateCHN, stateCode, stateEmoji, specialistCode

rpath, wAns = os.path.expanduser('~') + "/Retail/Jobs/", ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"
with open(rpath + "savedJobs.txt") as m: mark = m.read()
#stateCHN, stateCode, stateEmoji, specialistCode = ["澳大利亚"], ["AU"], ["🇦🇺"], [7991] #Debug

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')
logging.info("程序启动")

for scn, scd, ste, spl in zip(stateCHN, stateCode, stateEmoji, specialistCode):
	realCode = "11443" + str(spl)
	savename = rpath + scd + "/state.json"
	while True:
		logging.info("正在下载" + scn + "的国家文件")
		os.system("wget -t 20 -T 5 -O " + savename + " https://jobs.apple.com/api" + 
		"/v1/jobDetails/PIPE-" + realCode + "/stateProvinceList")
		if os.path.getsize(savename) > 0: break
	with open(savename) as j: jRead = j.read()
	if "Maintenance" in jRead: 
		logging.error("遇到了 Apple 招聘页面维护"); break
	stateJSON = json.loads(jRead)["searchResults"]
	for i in stateJSON: 
		savename = rpath + scd + "/location_" + i["id"].replace("postLocation-", "") + ".json"
		while True:
			logging.info("正在下载" + scn + "下的城市文件 " + i["id"] + ".json")
			os.system("wget -t 20 -T 5 -O " + savename + " 'https://jobs.apple.com/api/v1/jobDetails/PIPE-" 
			+ realCode + "/storeLocations?searchField=stateProvince&fieldValue=" + i["id"] + "'")
			if os.path.getsize(savename) > 0: break
	for j in stateJSON: 
		savename = rpath + scd + "/location_" + j["id"].replace("postLocation-", "") + ".json"
		with open(savename) as j: jRead = j.read()
		if "Maintenance" in jRead: 
			logging.error("遇到了 Apple 招聘页面维护"); break
		cityJSON = json.loads(jRead)
		for c in cityJSON:
			rolloutCode = c["code"]
			if not rolloutCode in mark:
				logging.info("找到了" + scn + "新店 " + rolloutCode + " 不在已知列表中")
				wAns += ste + rolloutCode + ", "
				pushAns = ("新店新机遇: " + ste + scn + "新增招聘地点 " + c["name"]
				+ ", 代号 " + rolloutCode + ", 文件名 " + j["id"].replace("postLocation-", "") + ".json")
				logging.info("[运行结果] " + pushAns)
				IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", IFTTT.getkey(), 0)
if wAns != "":
	logging.info("正在更新 savedJobs 文件")
	with open(rpath + "savedJobs.txt", "w") as m:
		m.write(mark + wAns)

logging.info("程序结束")