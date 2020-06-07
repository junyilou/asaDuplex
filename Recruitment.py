import os, json, time, logging
import IFTTT

stateCHN = ["新加坡", "土耳其", "阿联酋", "英国", "德国", "台湾", "美国", 
"墨西哥", "瑞士", "比利时", "荷兰", "泰国", "西班牙", "香港", "瑞典", "中国", 
"法国", "澳大利亚", "意大利", "澳门", "巴西", "日本", "韩国", "加拿大", "奥地利"]

stateCode = ["SG", "TR", "AE", "UK", "DE", "TW", "US", 
"MX", "CH", "BE", "NL", "TH", "ES", "HK", "SE", "CN", 
"FR", "AU", "IT", "MO", "BR", "JP", "KR", "CA", "AT"]

stateEmoji = ["🇸🇬", "🇹🇷", "🇦🇪", "🇬🇧", "🇩🇪", "🇹🇼", "🇺🇸", 
"🇲🇽","🇨🇭", "🇧🇪", "🇳🇱", "🇹🇭", "🇪🇸", "🇭🇰", "🇸🇪", "🇨🇳", 
"🇫🇷", "🇦🇺", "🇮🇹", "🇦🇹", "🇲🇴", "🇧🇷", "🇯🇵", "🇰🇷", "🇨🇦", "🇦🇹"]

specialistCode = [8238, 8164, 8225, 8145, 8043, 8311, 8158, 
8297, 8017, 8251, 8119, 8346, 8056, 8082, 8132, 8030, 8069,
7991, 8095, 8282, 8176, 8107, 8326, 8004, 8333]

rpath, wAns = os.path.expanduser('~') + "/Retail/Jobs/", ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"
with open(rpath + "savedJobs.txt") as m: mark = m.read()
#stateCHN, stateCode, stateEmoji, specialistCode = ["澳大利亚"], ["AU"], ["🇦🇺"], [7991] #Debug

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
				logging.info("找到了" + scn + "的新店 " + rolloutCode + " 不在已知列表中")
				wAns += ste + rolloutCode + ", "
				pushAns = ("新店新机遇: " + ste + scn + "新增招聘地点 " + c["name"]
				+ ", 代号 " + rolloutCode + ", 文件名 " + os.path.basename(savename))
				logging.info("[运行结果] " + pushAns)
				IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", IFTTT.getkey(), 0)
if wAns != "":
	logging.info("正在更新 savedJobs 文件")
	with open(rpath + "savedJobs.txt", "w") as m:
		m.write(mark + wAns)

logging.info("程序结束")