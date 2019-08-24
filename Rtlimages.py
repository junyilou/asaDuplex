#-*- coding:utf-8 -*-
import os, sys, json, time, IFTTT, PID
import json_tools

def fileOpen(fileloc):
	try: defOpen = open(fileloc); defReturn = defOpen.read(); defOpen.close()
	except IOError: return "No such file or directory."
	else: return defReturn

def pastebin(pin):
	print "Querying Pastebin API..."
	os.system("wget -q -t 100 -T 5 --no-check-certificate --post-data 'api_dev_key=\
47477216df13753adb7dcbd2600fc225&api_user_key=68978343239b4f6189909e34e5e8b0a3\
&api_paste_code=" + pin.replace("'", '|').replace('"', '|') + "&api_paste_name=\
storeList changelog&api_paste_expire_date=1W&api_option=paste&api_paste_format=\
json' -O " + rpath + "pasteTemp https://pastebin.com/api/api_post.php")
	pasteURL = fileOpen(rpath + "pasteTemp")
	os.system("rm " + rpath + "pasteTemp"); return pasteURL

def asa():
	global upb, asaVersion
	formatAsaVersion = int("".join(asaVersion.split("."))); print "Comparing ASA remote version..."
	os.system("wget -t 100 -T 5 -q -O " + rpath + "iTunesLookup https://itunes.apple.com/cn/lookup?id=375380948")
	try: remoteAsaVersion = int("".join(json.loads(fileOpen(rpath + "iTunesLookup"))["results"][0]["version"].split(".")))
	except: remoteAsaVersion = 0
	if remoteAsaVersion > 0 and remoteAsaVersion < 100: remoteAsaVersion *= 10
	if remoteAsaVersion > formatAsaVersion:
		asaVersion = ".".join(list(str(remoteAsaVersion)))
		asaupd = "Found newer ASA version " + asaVersion + ",\nreplaced older version " + asaVersion + "."
		upb += asaupd + "\n"; print asaupd
	print "Comparing ASA remote file..."
	listLoc = rpath + "storeList.json"
	orgListSize = os.path.getsize(listLoc)
	os.system("mv " + listLoc + " " + listLoc.replace(".json", "_old.json"))
	os.system("wget -t 100 -T 5 -q -U ASA/" + asaVersion + " -O " + listLoc + " --header 'x-ma-pcmh: REL-" + 
		asaVersion + "' https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite")
	newListSize = os.path.getsize(listLoc)
	if orgListSize != newListSize and orgListSize > 1024 and newListSize > 1024 :
		deltaListSize = newListSize - orgListSize
		if deltaListSize % 83:
			newLocation = listLoc.replace(".json", "_old.json"); oldTime = str(int(time.time()))
			oldLocation = listLoc.replace(".json", "_" + oldTime + ".json")
			os.system("mv " + newLocation + " " + oldLocation)
			newJSON = json.loads(fileOpen(listLoc)); oldJSON = json.loads(fileOpen(oldLocation))
			compareAns = pastebin(str(json.dumps(json_tools.diff(newJSON, oldJSON))))
			IFTTT.pushbots(
				"Apple Store app 的列表更新了：文件时间戳 " + oldTime + "，文件大小差异为 " + str(deltaListSize) + " 字节。",
				"https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_small_2x.jpg",
				compareAns, "linkraw", masterKey[0], 0)
		else: os.system("mv " + listLoc.replace(".json", "_old.json") + " " + listLoc)
	else: 
		os.system("mv " + listLoc.replace(".json", "_old.json") + " " + listLoc)
		print "No changes found."
	if newListSize == 0: print "ASA file download failed\nIs the current REL still signing?"

def down(rtl, isSpecial):
	global upb, exce; spr = "R" + rtl + ".png"; sx = sbn + rtl + ".png"
	if os.path.isfile(sx): oldsize = os.path.getsize(sx)
	else: oldsize = 0
	os.system("wget -U ASA/" + asaVersion + " -t 100 -T 5 -q -N -P " + rpath + "Pictures/ " + dieter + spr)
	if os.path.isfile(sx): newsize = os.path.getsize(sx)
	else: newsize = 0
	if newsize != oldsize and newsize > 1:
		try: rname = storejson['name'][rtl]; rflag = storejson['flag'][rtl]; rnso = storejson['nso'][rtl]
		except KeyError: rname = "Store"; rflag = ""; rnso = ""
		if rnso != "" and rnso != "TBC": 
			rnso = time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d"))
			reload(sys); sys.setdefaultencoding('utf-8'); rnso = "这家零售店最早开幕于 " + rnso + "。"
		pushRaw = ("Apple " + rname + " (R" + rtl + ") just updated,\n" + 
			"the size of the picture is " + str(newsize / 1024) + " KB.")
		upb += pushRaw + "\n"; print pushRaw
		if isSpecial: exce += rtl + ", "
		tellRaw = "零售店编号 R" + rtl + "，新图片的大小是 " + str(newsize / 1024) + " KB。" + rnso
		imageURL = dieter + spr + "?output-format=jpg"
		IFTTT.pushbots(tellRaw, rflag + "Apple " + rname + " 图片更新", imageURL, "raw", masterKey, 0)
	elif isSpecial:
			try: pname = "R" + rtl + ": " + storejson['name'][rtl]
			except KeyError: pname = "R" + rtl
			if newsize == 0: print pid + " Checked " + pname + " does not exist, ignore."
			else: print pid + " Checked "+ pname + " has no update, ignore."

global upb, asaVersion;
totalStore = 901; asaVersion = "5.5.0"
pid = str(os.getpid()); upb = exce = ""; arg = rTime = 0
for m in sys.argv[1:]: arg += 1
rpath = os.path.expanduser('~') + "/Retail/"; masterKey = IFTTT.getkey()
sbn = rpath + "Pictures/R"; storejson = json.loads(fileOpen(rpath + "storeInfo.json"))
PID.addCurrent(os.path.basename(__file__), os.getpid())
dieter = "https://rtlimages.apple.com/cmc/dieter/store/16_9/"

if arg == 1 and sys.argv[1] == "0": asa(); exit()

while True:
	reload(sys); sys.setdefaultencoding('utf-8')
	sTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()); eCount = exce.count(", ")
	if arg - eCount:
		print "Refreshing special stores: " + str(rTime % 18 + 1) + "/18"
		for s in sys.argv[1:]: 
			if not s in exce: down(s, True)
	else: print "No store was asked to watch: " + str(rTime % 18 + 1) + "/18"
	if not (rTime % 18):
		for j in range(1, totalStore): 
			down("%03d" % j, False)
			print pid + " Compare in Progress: " + str((j + 1) * 100 / totalStore) + "% on R" + "%03d" % j + "\r",
			sys.stdout.flush()
	print; asa(); rTime += 1
	print upb + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n"
	time.sleep(1200)