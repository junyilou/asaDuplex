import os, sys, json, time, IFTTT, PID, prettytable

def down(rtl, isSpecial):
	global logTable, exce
	spr = "R" + rtl + ".png"
	sx = rpath + "Pictures/R" + rtl + ".png"
	if os.path.isfile(sx): oldsize = os.path.getsize(sx)
	else: oldsize = 0
	os.system("wget -U ASA/" + asaVersion + " -t 100 -T 5 -q -N -P " + rpath + "Pictures/ " + dieter + spr)
	if os.path.isfile(sx): newsize = os.path.getsize(sx)
	else: newsize = 0
	if newsize != oldsize and newsize > 1:
		try: rname = storejson['name'][rtl]; rflag = storejson['flag'][rtl]; rnso = storejson['nso'][rtl]
		except KeyError: rname = "Store"; rflag = ""; rnso = ""
		if rnso != "" and rnso != "TBC": rnso = "这家零售店最早开幕于 " + time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d")) + "。"
		logTable.add_row([rtl, rname, time.strftime("%F %T", time.localtime()), str(int(newsize / 1024)) + " KB"])
		if isSpecial: exce += rtl + ", "
		tellRaw = "零售店编号 R" + rtl + "，新图片的大小是 " + str(int(newsize / 1024)) + " KB。" + rnso
		imageURL = dieter + spr + "?output-format=jpg"
		IFTTT.pushbots(tellRaw, rflag + "Apple " + rname + " 图片更新", imageURL, "raw", masterKey, 0)
	elif isSpecial:
			try: pname = "Apple " + storejson['name'][rtl] + " (R" + rtl + ")"
			except KeyError: pname = "Apple Store (R" + rtl + ")"  
			if newsize == 0: print(pid + " 检查到 " + pname + " 的图片服务器中不存在")
			else: print(pid + " 检查到 "+ pname + " 的图片没有更新")

global logTable
totalStore = 901
asaVersion = "5.6.0"
pid = str(os.getpid())
exce = ""; arg = rTime = 0
masterKey = IFTTT.getkey()
for m in sys.argv[1:]: arg += 1
rpath = os.path.expanduser('~') + "/Retail/"
sOpen = open(rpath + "storeInfo.json")
storejson = json.loads(sOpen.read()); sOpen.close()
PID.addCurrent(os.path.basename(__file__), os.getpid())
dieter = "https://rtlimages.apple.com/cmc/dieter/store/16_9/"
logTable = prettytable.PrettyTable()
logTable.field_names = ["ID", "Name", "Time", "Note"]; logTable.sortby = "Time"

while True:
	tempTable = logTable
	if arg - exce.count(", "):
		print("正在刷新特别零售店 [第 " + str(rTime % 18 + 1) + " 次, 共 18 次]")
		for s in sys.argv[1:]: 
			if not s in exce: down(s, True)
	else: print("没有指定特别刷新零售店 [第 " + str(rTime % 18 + 1) + " 次, 共 18 次]")
	if not (rTime % 18):
		for j in range(1, totalStore): 
			down("%03d" % j, False)
			print(pid + " 已完成 " + str(int((j + 1) * 100 / totalStore)) + "%, 目前 R" + "%03d" % j + "\r", end = "")
			sys.stdout.flush()
	print(time.strftime("\n%F %T", time.localtime())); rTime += 1
	if tempTable != logTable:
		print(logTable.get_string(title = "新控制台"), "\n")
	time.sleep(600)