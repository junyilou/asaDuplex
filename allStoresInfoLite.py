import os, time, json, filecmp, difflib, logging, requests
import IFTTT

asaVersion = "5.9.0"; remoteAsaVersion = 0
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

def fileOpen(fileloc):
	try: 
		with open(fileloc) as fin:
			return fin.read()
	except FileNotFoundError:
		logging.error(fileloc + " 文件不存在")
		return None

def fileWrite(fileloc, writer): 
	with open(fileloc, "w") as fout:
		fout.write(writer)

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

logging.info("正在确认远程 Apple Store app 文件...")
listLoc = rpath + "storeList.json"
orgListSize = os.path.getsize(listLoc)
os.system("mv " + listLoc + " " + listLoc.replace(".json", "-old.json"))
newLocation = listLoc.replace(".json", "-old.json")
os.system("wget -t 20 -T 5 -U ASA/" + asaVersion + " -O " + listLoc + " --header 'x-ma-pcmh: REL-" + 
	asaVersion + "' https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite")
newListSize = os.path.getsize(listLoc); dlc = fileOpen(listLoc)
fileWrite(listLoc, dlc.replace('?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*', ''))

runTime = time.strftime("%F", time.localtime())

if filecmp.cmp(newLocation, listLoc) == False and orgListSize and newListSize and "Jiefangbei" in dlc:
	logging.info("检测到有文件变化，正在生成 changeLog")
	deltaListSize = newListSize - orgListSize
	fileLines = []
	fileDiff = '<!DOCTYPE html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>'
	fileDiff += "storeList changeLog " + runTime + "</title></head><body><pre><code>"
	fileDiff += "Generated at " + runTime + " GMT+8\n"
	for formatFile in [newLocation, listLoc]:
		formatJSON = json.dumps(json.loads(fileOpen(formatFile)), ensure_ascii = False, indent = 2)
		fileLines.append(formatJSON.split("\n"))
		if formatFile == listLoc: fileWrite(listLoc.replace(".json", "-format.json"), formatJSON)
	for line in difflib.unified_diff(fileLines[0], fileLines[1]): fileDiff += line + "\n"
	fileWrite("/home/storelist.html", fileDiff + "</code></pre></body></html>")
	os.system("mv " + newLocation + " " + listLoc.replace(".json", "-" + runTime + ".json"))
	logging.info("文件生成完成，上一版本已保存至 storeList-" + runTime + ".json")
	pushAns = "检测到 Apple Store 零售店信息文件更新，文件大小差异 " + str(deltaListSize) + " 字节"
	logging.info("[运行结果] " + pushAns)
	IFTTT.pushbots(pushAns, "https://www.apple.com/jp/retail/store/includes/marunouchi/drawer/images/store-drawer-tile-1_small_2x.jpg",
		"http://myv.ps/storelist.html", "linkraw", IFTTT.getkey()[0], 0)
elif newListSize == 0: 
	logging.error("未能成功下载 allStoresInfoLite 文件")
elif dlc.count("Jiefangbei") == 0:
	os.system("mv " + listLoc.replace(".json", "-old.json") + " " + listLoc)
	logging.error("所下载的 allStoresInfoLite 文件似乎不是英语版本")
else: 
	os.system("mv " + listLoc.replace(".json", "-old.json") + " " + listLoc)
	logging.info("没有发现 storeList 文件更新")
logging.info("程序结束")