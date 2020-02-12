import os, sys, json, time, logging, IFTTT

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')

def down(rtl, isSpecial):
	spr = "R" + rtl + ".png"
	sx = rpath + "Pictures/R" + rtl + ".png"
	if os.path.isfile(sx): 
		oldsize = os.path.getsize(sx)
	else: 
		oldsize = 0
	os.system("wget -U ASA/" + asaVersion + " -t 100 -T 5 -N -P " + rpath + "Pictures/ " + dieter + spr)
	if os.path.isfile(sx): 
		newsize = os.path.getsize(sx)
	else: 
		newsize = 0
	if newsize != oldsize and newsize > 1:
		logging.info("监测到 R" + rtl + " 有更新")
		try: 
			rname = storejson['name'][rtl]
			rflag = storejson['flag'][rtl]
			rnso = storejson['nso'][rtl]
		except KeyError: 
			rname = "Store"
			rflag = ""; rnso = ""
		if rnso != "" and rnso != "TBC": 
			rnso = "这家零售店最早开幕于 " + time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d")) + "。"
		if isSpecial: 
			exce += rtl + ", "
		tellRaw = "零售店编号 R" + rtl + "，新图片的大小是 " + str(int(newsize / 1024)) + " KB。" + rnso
		imageURL = dieter + spr + "?output-format=jpg"
		titaru = rflag + "Apple " + rname + " 图片更新"
		logging.info("[运行结果] " + titaru + "，" + tellRaw)
		IFTTT.pushbots(tellRaw, titaru, imageURL, "raw", masterKey, 0)
	elif isSpecial:
		try: pname = "Apple " + storejson['name'][rtl] + " (R" + rtl + ")"
		except KeyError: pname = "Apple Store (R" + rtl + ")"  
		if newsize == 0: logging.info("检查到 " + pname + " 的图片服务器中不存在")
		else: logging.info("检查到 "+ pname + " 的图片没有更新")

totalStore = 901
asaVersion = "5.7.0"
masterKey = IFTTT.getkey()
rpath = os.path.expanduser('~') + "/Retail/"
with open(rpath + "storeInfo.json") as s:
	storejson = json.loads(s.read())
dieter = "https://rtlimages.apple.com/cmc/dieter/store/16_9/"

if sys.argv[1] == "normal":
	logging.info("开始枚举零售店")
	a = 100
	for j in range(1, totalStore):
		down("%03d" % j, False)
		if j == a:
			logging.info("已完成 " + str(int(a / 100)) + "/9")
			a += 100
	logging.info("程序结束")

if sys.argv[1] == "special":
	with open(rpath + "specialist.txt") as l:
		specialist = l.read().replace("\n", "").split(", ")
		try: specialist.remove('')
		except ValueError: pass
	if len(specialist):
		logging.info("开始特别观察模式")
		for i in specialist:
			down(i, True)