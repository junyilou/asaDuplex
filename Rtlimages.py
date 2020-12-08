import os, sys, json, time, logging, requests
import telegram

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
requests.packages.urllib3.disable_warnings()

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, datefmt = '%T')

def down(rtl, isSpecial):
	base = dieter + "R" + rtl + ".png"
	try: rmod = storejson['last'][rtl]
	except KeyError: rmod = ""
	r = requests.head(base, allow_redirects = True, verify = False)
	if r.status_code == 404:
		if isSpecial:
			logging.info("检查到 R" + rtl + " 的图片服务器中不存在")
		return
	if r.headers['Last-Modified'] != rmod:
		logging.info("监测到 R" + rtl + " 有更新，正在保存图片")
		savename = rpath + "R" + rtl + "_" + r.headers['Last-Modified'].replace(" ", "").replace(",", "").replace(":", "") + ".png"
		os.system("wget -O " + savename + " " + base)
		try: 
			rname = storejson['name'][rtl]
			rflag = storejson['flag'][rtl]
			rnso = storejson['nso'][rtl]
		except KeyError: 
			rname = "Store"
			rflag = ""; rnso = ""
		if rnso != "" and rnso != "TBC": 
			rnso = "最先开幕于 " + time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d"))
		if isSpecial: 
			specialist.remove(rtl)
			with open(rpath + "specialist.txt", "w") as w:
				w.write(", ".join(specialist))
		storejson['last'][rtl] = r.headers['Last-Modified']
		storejson['last'] = dict([(k, storejson['last'][k]) for k in sorted(storejson['last'].keys())])
		logging.info("正在更新 storeInfo.json")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open(rpath + "storeInfo.json", "w") as sw:
			sw.write(sOut)

		tellRaw = rflag + " Apple " + rname + " (R" + rtl + ") 图片更新\n修改标签 " + r.headers['Last-Modified'] + "，" + rnso
		logging.getLogger().setLevel(logging.DEBUG)
		bot = telegram.Bot(token = token)
		bot.send_photo(
			chat_id = chat_id, 
			photo = base,
			caption = '*来自 Rtlimages 的通知*\n' + tellRaw,
			parse_mode = 'Markdown')
		logging.getLogger().setLevel(logging.INFO)

	elif isSpecial:
		try: pname = "Apple " + storejson['name'][rtl] + " (R" + rtl + ")"
		except KeyError: pname = "Apple Store (R" + rtl + ")"  
		logging.info("检查到 "+ pname + " 的图片没有更新")

totalStore = 901
asaVersion = "5.9.0"
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