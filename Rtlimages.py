import os, sys, json, time, logging, requests, IFTTT

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.INFO, filemode = 'a', datefmt = '%F %T %p')

def down(rtl, isSpecial):
	base = dieter + "R" + rtl + ".png"
	try: rmod = storejson['last'][rtl]
	except KeyError: rmod = ""
	r = requests.head(base, allow_redirects = True)
	if r.status_code != 200: return 0
	if r.headers['Last-Modified'] != rmod:
		logging.info("监测到 R" + rtl + " 有更新，正在保存图片")
		os.system("wget -O " + rpath + "R" + rtl + "_" +
			r.headers['Last-Modified'].replace(" ", "").replace(",", "") + ".png " + base)
		try: 
			rname = storejson['name'][rtl]
			rflag = storejson['flag'][rtl]
			rnso = storejson['nso'][rtl]
		except KeyError: 
			rname = "Store"
			rflag = ""; rnso = ""
		if rnso != "" and rnso != "TBC": 
			rnso = "该店开幕于 " + time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d")) + "。"
		if isSpecial: 
			specialist.remove(rtl)
			with open(rpath + "specialist.txt", "w") as w:
				w.write(", ".join(specialist))
		tellRaw = "零售店编号 R" + rtl + "，新图片的最后修改标签是 " + r.headers['Last-Modified'] + "。" + rnso
		titaru = rflag + "Apple " + rname + " 图片更新"
		logging.info("[运行结果] " + titaru + "，" + tellRaw)
		IFTTT.pushbots(tellRaw, titaru, base + "?output-format=jpg", "raw", masterKey, 0)
	elif isSpecial:
		try: pname = "Apple " + storejson['name'][rtl] + " (R" + rtl + ")"
		except KeyError: pname = "Apple Store (R" + rtl + ")"  
		if r.status_code == 404: logging.info("检查到 " + pname + " 的图片服务器中不存在")
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