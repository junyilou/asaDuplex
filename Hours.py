from storeInfo import *
from special import speHours

import json, os, logging, telegram
from datetime import datetime, date
from sys import stdout

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

### *** EDIT START *** ###
args = {'s': ['🇨🇳', '🇭🇰', '🇲🇴', 'TW']}
### *** EDIT  END  *** ###

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, datefmt = '%T')

logging.info("程序启动")
runtime = datetime.now().strftime("%F")

stores = list()
functions = {'r': StoreID, 'n': StoreName, 's': StoreNation}
for f in functions.keys():
	if f in args.keys():
		S = map(functions[f], args[f])
		for _s in list(S):
			for __s in _s:
				if __s not in stores:
					stores.append(__s)
try:
	stores.sort(key = lambda k: storeOrder().index("R" + k[0]))
except ValueError:
	logging.error("未能成功对请求的零售店按地区进行排序")
	pass

comparison = ""
calendar = {}
allSpecial = {"created": runtime}

try: 
	with open("Retail/storeHours.json") as o:
		orgjson = json.loads(o.read())
except FileNotFoundError: 
	orgjson = {}
	with open("Retail/storeHours.json", "w") as w:
		w.write("{}")

for sid, sn in stores:
	cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 20)
	print("[{:=^{}}{:^{}}] R{} {}/{} {:.1%}".format("", perc, "", 20 - perc, sid, cur, tot, cur / tot), end = "\r")
	stdout.flush()

	specialHours = speHours(sid)
	storeDiff = ""

	if len(specialHours):
		allSpecial[sid] = {"storename": sn, **specialHours}

	for s in specialHours:
		fSpecial = specialHours[s]["special"]

		if s in calendar.keys():
			calendar[s][sn] = fSpecial
		else:
			calendar[s] = {sn: fSpecial}

		try: 
			orgSpecial = orgjson[sid][s]["special"]
		except KeyError:
			storeDiff += " " * 8 + "{}：新增 {}\n".format(s, fSpecial)
		else: 
			if orgSpecial != fSpecial:
				storeDiff += " " * 8 + "{}：由 {} 改为 {}\n".format(s, orgSpecial, fSpecial)

	try: 
		oload = orgjson[sid]
	except KeyError: 
		pass
	else:
		for odate in oload.keys():
			if odate == "storename": 
				continue
			odatetime = datetime.strptime(odate, '%Y-%m-%d').date()
			if odatetime < date.today(): 
				continue
			try:
				newSpecial = specialHours[odate]
			except KeyError:
				storeDiff += " " * 8 + "{}：取消 {}\n".format(odate, oload[odate]["special"])

	if len(storeDiff):
		comparison += "    Apple {}\n{}".format(sn, storeDiff)

os.rename("Retail/storeHours.json", "Retail/storeHours-" + runtime + ".json")

logging.info("写入新的 storeHours.json")
jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
calendar = dict(sorted(calendar.items(), key = lambda k: k[0]))
calendar = json.dumps(calendar, ensure_ascii = False, indent = 2)
with open("Retail/storeHours.json", "w") as w:
	w.write(jOut)

if len(comparison):
	fileDiff = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>specialHours</title>
</head>

<body><pre><code>
Apple Store 特别营业时间
生成于 {}\n\n
变化：\n{}\n
日历:\n{}\n\n
原始 JSON:\n{}
</code></pre></body></html>
""".format(runtime, comparison, calendar, jOut)
	with open("/home/storeHours.html", "w") as w:
		w.write(fileDiff)
	logging.info("文件生成完成")

	logging.getLogger().setLevel(logging.DEBUG)
	bot = telegram.Bot(token = token)
	bot.send_photo(
		chat_id = chat_id,
		photo = "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_medium_2x.jpg",
		caption = '*来自 Hours 的通知*\n{} 个 Apple Store 有特别营业时间变化\n\nhttps://shunitsu.moe/storeHours.html'.format(comparison.count("Apple")),
		parse_mode = 'Markdown')
	logging.getLogger().setLevel(logging.INFO)

else: 
	os.remove("Retail/storeHours-{}.json".format(runtime))
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")