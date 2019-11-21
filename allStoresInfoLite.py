import os, time, json, filecmp, difflib, IFTTT, PID

asaVersion = "5.6.0"
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

def fileOpen(fileloc):
	try: defOpen = open(fileloc); defReturn = defOpen.read(); defOpen.close()
	except IOError: return "No such file or directory."
	else: return defReturn

def fileWrite(fileloc, writer): defWrite = open(fileloc, "w"); defWrite.write(writer); defWrite.close()

print("正在确认远程 Apple Store app 版本...")
os.system("wget -t 100 -T 5 -q -O " + rpath + "iTunesLookup https://itunes.apple.com/cn/lookup?id=375380948")
try: remoteAsaVersion = int("".join(json.loads(fileOpen(rpath + "iTunesLookup"))["results"][0]["version"].split(".")))
except: remoteAsaVersion = 0
if remoteAsaVersion > 0 and remoteAsaVersion < 100: remoteAsaVersion *= 10
if remoteAsaVersion > formatAsaVersion:
	asaVersion = ".".join(list(str(remoteAsaVersion)))
	logTable.add_row(["000", "appVersion", time.strftime("%F %T", time.localtime()), asaVersion])
	print("从远程获得了新的 Apple Store app 版本 " + asaVersion)

print("正在确认远程 Apple Store app 文件...")
listLoc = rpath + "storeList.json"
orgListSize = os.path.getsize(listLoc)
os.system("mv " + listLoc + " " + listLoc.replace(".json", "-old.json"))
newLocation = listLoc.replace(".json", "-old.json")
os.system("wget -t 100 -T 5 -q -U ASA/" + asaVersion + " -O " + listLoc + " --header 'x-ma-pcmh: REL-" + 
	asaVersion + "' https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite")
newListSize = os.path.getsize(listLoc)
fileWrite(listLoc, fileOpen(listLoc).replace('?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*', ''))

runTime = time.strftime("%F %T", time.localtime())

if not filecmp.cmp(newLocation, listLoc) and orgListSize > 1024 and newListSize > 1024 :
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
	fileWrite(rpath + "changeLog-" + changeTime + ".html", fileDiff + "</code></pre></body></html>")
	os.system("mv " + newLocation + " " + listLoc.replace(".json", "-" + changeTime + ".json"))
	os.system("mv " + rpath + "changeLog-" + changeTime + ".html /root/www/changeLog-latest.html")
	IFTTT.pushbots("于 " + time.strftime("%Y 年 %-m 月 %-d 日 %-H:%M ", time.localtime()) 
		+ "检测到更新，大小差异 " + str(deltaListSize) + " 字节，编号 changeLog-" + changeTime, "Apple Store app 文件更新", 
		"https://www.apple.com/jp/retail/store/includes/marunouchi/drawer/images/store-drawer-tile-1_small_2x.jpg", 
		"raw", IFTTT.getkey()[0], 0)
	print("已经更新本地 storeList 文件 " + runTime)
elif newListSize == 0: 
	print("未能下载 allStoresInfoLite 文件 " + runTime)
else: 
	os.system("mv " + listLoc.replace(".json", "-old.json") + " " + listLoc)
	print("没有发现 storeList 文件更新 " + runTime)