import json, datetime, os, logging, time, IFTTT, requests
from retailData import storename, storeID

asaVersion = "5.8.0"; remoteAsaVersion = 0
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

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
runtime = datetime.datetime.now().strftime("%F")

def tttf(raw):
	rawtime = raw[2:].split(":"); hrs = rawtime[0]
	if '上午' in raw:
		if hrs == "12": fhrs = 0
		else: fhrs = int(hrs)
	if '下午' in raw:
		if hrs == "12": fhrs = 12
		else: fhrs = int(hrs) + 12
	return (fhrs, int(rawtime[1]))

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

logging.info("正在确认远程 Apple Store app 版本...")
try: 
	lookup = requests.get("https://itunes.apple.com/cn/lookup?id=375380948").json()
except: pass
else: 
	remoteAsaVersion = int("".join(lookup["results"][0]["version"].split(".")))
if remoteAsaVersion in range(10, 101): remoteAsaVersion *= 10
if remoteAsaVersion > formatAsaVersion:
	asaVersion = ".".join(list(str(remoteAsaVersion)))
	logging.info("从远程获得了新的 Apple Store app 版本 " + asaVersion)

for i in storeID:
	listLoc = rpath + "storeDeatils-R" + str(i) + ".txt"
	logging.info("正在下载零售店 R" + str(i) + " 的细节文件...")
	os.system("wget -t 20 -T 5 -U ASA/" + asaVersion + " -O " + listLoc + 
	" --header 'x-ma-pcmh: REL-" + asaVersion + "'" + 
	" --header 'X-DeviceConfiguration: vv=" + asaVersion + ";sv=13.3' " +
	" --header 'X-MALang: zh-CN' " +
	"'https://mobileapp.apple.com/mnr/p/cn/retail/storeDetails?storeNumber=R" + str(i) + "'")

orgjson = json.loads(fileOpen(rpath + "storeHours.json"))
allSpecial = {"created": runtime}; comparison = ""

for sn, sid in zip(storename, storeID):
	storejson = fileOpen(rpath + "storeDeatils-R" + str(sid) + ".txt")
	storedict = json.loads(storejson)["allStoreHoursMergedResponse"]
	storeDiff = ""

	try: 
		special = storedict["specialHours"]
	except: 
		special = []
	storeSpecial = {}; storeComment = {}
	for s in special:
		sWeekday = datetime.datetime.strptime(s["specialDate"], '%Y年%m月%d日').weekday()
		if s["isClosed"] == "Y": 
			fSpecial = "CLOSED"
		else: 
			sTime = tttf(s["startTime"]); eTime = tttf(s["endTime"])
			fSpecial = str(sTime[0]) + ":" + "%02d" % sTime[1] + " - " + str(eTime[0]) + ":" + "%02d" % eTime[1]
		singleSpecial = {s["specialDate"]: fSpecial}
		singleComment = {s["specialDate"]: "[" + s["reason"] + "]" + s["comments"]}
		storeSpecial = {**storeSpecial, **singleSpecial}
		storeComment = {**storeComment, **singleComment}
		try: 
			orgSpecial = orgjson[str(sid)]["time"][s["specialDate"]]
		except KeyError:
			storeDiff += " " * 8 + s["specialDate"] + "：新增 " + fSpecial + "\n"
			logging.info("Apple " + sn + " " + s["specialDate"] + " 新增 " + fSpecial)
		else: 
			if orgSpecial != fSpecial:
				storeDiff += " " * 8 + s["specialDate"] + "：由 " + orgSpecial + " 改为 " + fSpecial + "\n"
				logging.info("Apple " + sn + " " + s["specialDate"] + " 改为 " + fSpecial)
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
				storeDiff += " " * 8 + odate + "：取消 " + oload[odate] + "\n"
				logging.info("Apple " + sn + " " + odate + " 取消 " + oload[odate])
	if len(storeSpecial):
		addSpecial = {sid: {"storename": sn, "time": storeSpecial, "comment": storeComment}}
		allSpecial = {**allSpecial, **addSpecial}
	if len(storeDiff):
		comparison += "    Apple " + sn + "\n" + storeDiff
	os.remove(rpath + "storeDeatils-R" + str(sid) + ".txt")

jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
os.system("mv " + rpath + "storeHours.json " + rpath + "storeHours-" + runtime + ".json")
fileWrite(rpath + "storeHours.json", jOut)
logging.info("写入新的 storeHours.json")

if len(comparison):
	tOut = "Apple Store 特别营业时间\n生成于 " + runtime + "\n\n变化：\n" + comparison + "\n原始 JSON:\n" + jOut
	fileDiff = '<!DOCTYPE html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>'
	fileDiff += "storeHours " + runtime + "</title></head><body><pre><code>"
	fileDiff += tOut + "</code></pre></body></html>"
	fileWrite("/home/storeHours.html", fileDiff)
	logging.info("文件生成完成，上一版本已保存至 storeHours-" + runtime + ".json")
	pushAns = "监测到 Apple Store 零售店有 " + str(comparison.count("Apple")) + " 个特别营业时间变化，点击链接查看详细变化和原始 JSON 内容。"
	logging.info("[运行结果] " + pushAns)
	IFTTT.pushbots(pushAns, "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_small_2x.jpg",
		"http://myv.ps/storeHours.html", "linkraw", IFTTT.getkey()[0], 0)
else: 
	os.remove(rpath + "storeHours-" + runtime + ".json")
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")