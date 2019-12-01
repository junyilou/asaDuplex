import os, time, json, filecmp, difflib, logging, IFTTT

asaVersion = "5.6.0"
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')
logging.info("程序启动")

def fileOpen(fileloc):
	try: defOpen = open(fileloc); defReturn = defOpen.read(); defOpen.close()
	except IOError: 
		logging.error(fileloc + " 文件不存在")
		return None
	else: return defReturn

def fileWrite(fileloc, writer): defWrite = open(fileloc, "w"); defWrite.write(writer); defWrite.close()

logging.info("正在确认远程 Apple Store app 版本...")
os.system("wget -t 20 -T 5 -O " + rpath + "iTunesLookup https://itunes.apple.com/cn/lookup?id=375380948")
try: remoteAsaVersion = int("".join(json.loads(fileOpen(rpath + "iTunesLookup"))["results"][0]["version"].split(".")))
except: remoteAsaVersion = 0
if remoteAsaVersion > 0 and remoteAsaVersion < 100: remoteAsaVersion *= 10
if remoteAsaVersion > formatAsaVersion:
	asaVersion = ".".join(list(str(remoteAsaVersion)))
	logging.info("从远程获得了新的 Apple Store app 版本 " + asaVersion)

logging.info("正在确认远程 Apple Store app 文件...")
listLoc = rpath + "storeList.json"
orgListSize = os.path.getsize(listLoc)
os.system("mv " + listLoc + " " + listLoc.replace(".json", "-old.json"))
newLocation = listLoc.replace(".json", "-old.json")
os.system("wget -t 20 -T 5 -U ASA/" + asaVersion + " -O " + listLoc + " --header 'x-ma-pcmh: REL-" + 
	asaVersion + "' https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite")
newListSize = os.path.getsize(listLoc)
fileWrite(listLoc, fileOpen(listLoc).replace('?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*', ''))

runTime = time.strftime("%F %T", time.localtime())

if not filecmp.cmp(newLocation, listLoc) and orgListSize > 1024 and newListSize > 1024:
	logging.info("检测到有文件变化，正在生成 changeLog")
	deltaListSize = newListSize - orgListSize
	fileLines = []; changeTime = time.strftime("%Y%m%d-%H%M%S", time.localtime())
	fileDiff = '<!DOCTYPE html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>'
	fileDiff += "storeList changeLog " + changeTime + "</title></head><body><pre><code>"
	fileDiff += "Generated at " + changeTime + " GMT+8\n"
	for formatFile in [newLocation, listLoc]:
		formatJSON = json.dumps(json.loads(fileOpen(formatFile)), ensure_ascii = False, indent = 2)
		fileLines.append(formatJSON.split("\n"))
		if formatFile == listLoc: fileWrite(listLoc.replace(".json", "-format.json"), formatJSON)
	for line in difflib.unified_diff(fileLines[0], fileLines[1]): fileDiff += line + "\n"
	fileWrite("/root/www/changeLog-latest.html", fileDiff + "</code></pre></body></html>")
	os.system("mv " + newLocation + " " + listLoc.replace(".json", "-" + changeTime + ".json"))
	logging.info("文件生成完成，上一版本已保存至 storeList-" + changeTime + ".json")
	pushAns = "于 " + runTime + " 检测到更新，大小差异 " + str(deltaListSize) + " 字节"
	logging.info("[运行结果] " + pushAns)
	IFTTT.pushbots(pushAns, "https://www.apple.com/jp/retail/store/includes/marunouchi/drawer/images/store-drawer-tile-1_small_2x.jpg",
		"http://myv.ps/changeLog-latest.html", "linkraw", IFTTT.getkey()[0], 0)
elif newListSize == 0: 
	logging.error("未能下载 allStoresInfoLite 文件 " + runTime)
else: 
	os.system("mv " + listLoc.replace(".json", "-old.json") + " " + listLoc)
	logging.info("没有发现 storeList 文件更新")
logging.info("程序结束")