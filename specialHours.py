import json, datetime, os, logging, filecmp, time, difflib
from retailData import storename, storeID

asaVersion = "5.7.0"
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')
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
	if detm < 10: detm = "0" + str(detm)
	else: detm = str(detm)
	return (deth, detm)

def tdet(a, b):
	timeA = a[1] - a[0]
	timeB = b[1] - b[0]
	det = timeA - timeB
	if ftup(det)[0] == "0": return ftup(det)[1] + " 分钟"
	elif ftup(det)[1] == "00": return ftup(det)[0] + " 小时"
	else: return ftup(det)[0] + " 小时 " + ftup(det)[1] + " 分钟"

def fileOpen(fileloc):
	try: defOpen = open(fileloc); defReturn = defOpen.read(); defOpen.close()
	except IOError: 
		logging.error(fileloc + " 文件不存在")
		return None
	else: return defReturn

def fileWrite(fileloc, writer): defWrite = open(fileloc, "w"); defWrite.write(writer); defWrite.close()

transdict = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}
revtrans = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
specialist = {"generate": runtime}

logging.info("正在确认远程 Apple Store app 版本...")
#os.system("wget -t 20 -T 5 -O " + rpath + "iTunesLookup https://itunes.apple.com/cn/lookup?id=375380948")
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

for sn, sid in zip(storename, storeID):
	with open (rpath + "storeDeatils-R" + str(sid) + ".txt") as org: orgjson = org.read()
	orgdict = json.loads(orgjson)["allStoreHoursMergedResponse"]

	regular = orgdict["regularHours"]
	storeRegular = [(0, 0)] * 7
	for r in regular:
		rRange = r["range"].replace(":", "")
		if r["time"] != "不营业":
			rTime = r["time"].split(" – ")
			rStart = tttf(rTime[0]); rEnd = tttf(rTime[1])
			if rRange.count("周") == 1:
				storeRegular[transdict[rRange]] = (rStart, rEnd)
			else:
				startDay = rRange.split(" – ")[0]; endDay = rRange.split(" – ")[1]
				for d in range(transdict[startDay], transdict[endDay] + 1):
					storeRegular[d] = (rStart, rEnd)
	logging.info("取得 R" + str(sid) + " 的通常时间表")

	try: special = orgdict["specialHours"]
	except: special = []
	storeSpecial = []
	for s in special:
		sWeekday = datetime.datetime.strptime(s["specialDate"], '%Y年%m月%d日').weekday()
		if s["isClosed"] == "Y": sTime = (0, 0)
		else: sTime = (tttf(s["startTime"]), tttf(s["endTime"]))
		sRegular = storeRegular[sWeekday]
		fRegular = ftup(sRegular[0])[0] + ":" + ftup(sRegular[0])[1] + "-" + ftup(sRegular[1])[0] + ":" + ftup(sRegular[1])[1]
		fSpecial = ftup(sTime[0])[0] + ":" + ftup(sTime[0])[1] + "-" + ftup(sTime[1])[0] + ":" + ftup(sTime[1])[1]
		singleSpecial = {
			"name": sn,
			"date": s["specialDate"],
			"weekday": revtrans[sWeekday],
			"regular": fRegular,
			"special": fSpecial,
			"delta": tdet(sTime, sRegular),
			"reason": s["reason"],
			"comments": s.get("comments", "")
		}
		storeSpecial.append(singleSpecial)
	if len(storeSpecial):
		singleappend = {
			"R" + str(sid): storeSpecial
		}
		specialist = {**specialist, **singleappend}
	os.system("rm " + rpath + "storeDeatils-R" + str(sid) + ".txt")
	logging.info("生成了 R" + str(sid) + " 的单一列表")

newLocation = rpath + "storeHours-new.json"
listLoc = rpath + "storeHours.json"

fileWrite(rpath + "storeHours-new.json", json.dumps(specialist, ensure_ascii = False, indent = 2))

if not filecmp.cmp(rpath + "storeHours-new.json", rpath + "storeHours.json"):
	logging.info("检测到有文件变化，正在生成 changeLog")
	fileLines = []
	fileDiff = '<!DOCTYPE html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>'
	fileDiff += "storeHours changeLog " + runtime + "</title></head><body><pre><code>"
	fileDiff += "Generated at " + runtime + " GMT+8\n"
	for ftext in [fileOpen(newLocation), fileOpen(listLoc)]:
		fileLines.append(ftext.split("\n"))
	for line in difflib.unified_diff(fileLines[1], fileLines[0]): fileDiff += line + "\n"
	fileWrite("/root/www/storeHours.html", fileDiff + "</code></pre></body></html>")
	os.system("mv " + listLoc + " " + listLoc.replace(".json", "-" + runtime + ".json"))
	os.system("mv " + newLocation + " " + listLoc)
	logging.info("文件生成完成，上一版本已保存至 storeHours-" + runtime + ".json")
	pushAns = "监测到有新的特别营业时间，点击链接查看 DIFF 内容。"
	logging.info("[运行结果] " + pushAns)
	IFTTT.pushbots(pushAns, "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_small_2x.jpg",
		"http://myv.ps/storeHours.html", "linkraw", IFTTT.getkey()[0], 0)
else: 
	os.system("rm " + newLocation)
	logging.info("没有发现 storeHours 文件更新")
logging.info("程序结束")