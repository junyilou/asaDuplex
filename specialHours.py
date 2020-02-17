import json, datetime, os, logging, time, IFTTT
from retailData import storename, storeID

asaVersion = "5.7.0"
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'w', datefmt = '%F %T %p')
logging.info("程序启动")
runtime = datetime.datetime.now().strftime("%F")

def tttf(raw):
	rawtime = raw[2:].split(":"); hrs = rawtime[0]
	if '上午' in raw:
		if hrs == "12": fhrs = 0
		else: fhrs = int(hrs)
	if '下午' in raw:
		if hrs == "12": fhrs = 12
		else: fhrs = int(hrs) + 12
	return fhrs * 60 + int(rawtime[1])

def ftup(raw): 
	detm = raw % 60; deth = str(int((raw - detm) / 60))
	detm = "%02d" % detm
	return (deth, detm)

def fileWrite(fileloc, writer): 
	with open(fileloc, "w") as fout:
		fout.write(writer)

def fileOpen(fileloc):
	try: 
		with open(fileloc) as fin:
			return fin.read()
	except FileNotFoundError:
		logging.error(fileloc + " 文件不存在")
		return None

transdict = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
revtrans = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

logging.info("正在确认远程 Apple Store app 版本...")
os.system("wget -t 20 -T 5 -O " + rpath + "iTunesLookup https://itunes.apple.com/cn/lookup?id=375380948")
try: remoteAsaVersion = int("".join(json.loads(fileOpen(rpath + "iTunesLookup"))["results"][0]["version"].split(".")))
except: remoteAsaVersion = 0
if remoteAsaVersion > 0 and remoteAsaVersion < 100: remoteAsaVersion *= 10
if remoteAsaVersion > formatAsaVersion:
	asaVersion = ".".join(list(str(remoteAsaVersion)))
	logging.info("从远程获得了新的 Apple Store app 版本 " + asaVersion)

for i in storeID:
	listLoc = rpath + "storeDeatils-R" + str(i) + ".txt"
	logging.info("正在下载零售店 R" + str(i) + " 的细节文件...")
	os.system("wget -t 20 -T 5 -U ASA/5.7 -O " + listLoc + 
	" --header 'x-ma-pcmh: REL-" + asaVersion + "'" + 
	" --header 'X-DeviceConfiguration: vv=" + asaVersion + ";sv=13.3' " +
	" --header 'X-MALang: zh-CN' " +
	"'https://mobileapp.apple.com/mnr/p/cn/retail/storeDetails?storeNumber=R" + str(i) + "'")

orgjson = json.loads(fileOpen(rpath + "storeHours.json"))

allSpecial = {"created": runtime}
comparison = ""

for sn, sid in zip(storename, storeID):
	storejson = fileOpen(rpath + "storeDeatils-R" + str(sid) + ".txt")
	storedict = json.loads(storejson)["allStoreHoursMergedResponse"]

	try: 
		special = storedict["specialHours"]
	except: 
		special = []
	storeSpecial = {}
	for s in special:
		sWeekday = datetime.datetime.strptime(s["specialDate"], '%Y年%m月%d日').weekday()
		if s["isClosed"] == "Y": 
			fSpecial = "CLOSED"
		else: 
			sTime = (tttf(s["startTime"]), tttf(s["endTime"]))
			fSpecial = ftup(sTime[0])[0] + ":" + ftup(sTime[0])[1] + " - " + ftup(sTime[1])[0] + ":" + ftup(sTime[1])[1]
		singleSpecial = {s["specialDate"]: fSpecial}
		storeSpecial = {**storeSpecial, **singleSpecial}
		try: 
			orgSpecial = orgjson[str(sid)]["time"][s["specialDate"]]
		except KeyError:
			aOut = "+ Apple " + sn + " 在 " + s["specialDate"] + " 新增特别营业时间 " + fSpecial
			comparison += aOut + "\n"; logging.info("监测到 " + aOut)
		else: 
			if orgSpecial != fSpecial:
				aOut = "= Apple " + sn + " 在 " + s["specialDate"] + " 的特别营业时间由 " + orgSpecial + " 改为 " + fSpecial
				comparison += aOut + "\n"; logging.info("监测到 " + aOut)
	try: 
		oload = orgjson[str(sid)]["time"]
	except KeyError: 
		pass
	else:
		for odate in oload:
			odatetime = datetime.datetime.strptime(odate, '%Y年%m月%d日')
			if odatetime < datetime.datetime.now(): continue
			try:
				newSpecial = storeSpecial[odate]
			except KeyError:
				aOut = "- Apple " + sn + " 在 " + odate + " 的营业时间 " + oload[odate] + " 已被取消"
				comparison += aOut + "\n"; logging.info("监测到 " + aOut)
	if len(storeSpecial):
		addSpecial = {sid: {"storename": sn, "time": storeSpecial}}
		allSpecial = {**allSpecial, **addSpecial}
	os.remove(rpath + "storeDeatils-R" + str(sid) + ".txt")

jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
os.system("mv " + rpath + "storeHours.json " + rpath + "storeHours-" + runtime + ".json")
fileWrite(rpath + "storeHours.json", jOut)
logging.info("写入新的 storeHours.json")

if len(comparison):
	tOut = "Generated on: " + runtime + "\n\nChanges:\n" + comparison + "\nOriginal JSON:\n" + jOut
	fileDiff = '<!DOCTYPE html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>'
	fileDiff += "storeHours " + runtime + "</title></head><body><pre><code>"
	fileDiff += tOut + "</code></pre></body></html>"
	fileWrite("/root/www/storeHours.html", fileDiff)
	logging.info("文件生成完成，上一版本已保存至 storeHours-" + runtime + ".json")
	pushAns = "监测到 Apple Store 零售店有 " + str(comparison.count("Apple")) + " 个特别营业时间变化，点击链接查看详细变化和原始 JSON 内容。"
	logging.info("[运行结果] " + pushAns)
	IFTTT.pushbots(pushAns, "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_small_2x.jpg",
		"http://myv.ps/storeHours.html", "linkraw", IFTTT.getkey()[0], 0)
else: 
	os.remove(rpath + "storeHours-" + runtime + ".json")
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")