from storeInfo import *
from special import speHours

import json, os, logging, telegram
from datetime import datetime, date

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

stores = []; storen = []
functions = {'r': StoreID, 'n': StoreName, 's': StoreNation}
for f in functions.keys():
	if f in args.keys():
		S = map(functions[f], args[f])
		for _s in list(S):
			for __s in _s:
				if __s[0] not in stores:
					stores.append(__s[0])
					storen.append(__s[1])

logging.info("程序启动")
runtime = datetime.now().strftime("%F")

comparison = ""
allSpecial = {"created": runtime}
try: 
	with open("Retail/storeHours.json") as o:
		orgjson = json.loads(o.read())
except FileNotFoundError: 
	orgjson = {}
	with open("Retail/storeHours.json", "w") as w:
		w.write("{}")

for sid, sn in zip(stores, storen):
	specialHours = speHours(sid)
	storeDiff = ""

	if len(specialHours):
		allSpecial[sid] = {"storename": sn, **specialHours}

	for s in specialHours:
		fSpecial = specialHours[s]["special"]
		try: 
			orgSpecial = orgjson[sid][s]["special"]
		except KeyError:
			storeDiff += " " * 8 + "{}：新增 {}\n".format(s, fSpecial)
			logging.info("Apple {} {} 新增 {}".format(sn, s, fSpecial))
		else: 
			if orgSpecial != fSpecial:
				storeDiff += " " * 8 + "{}：由 {} 改为 {}\n".format(s, orgSpecial, fSpecial)
				logging.info("Apple {} {} 改为 {}".format(sn, s, fSpecial))

	try: 
		oload = orgjson[sid]
	except KeyError: 
		pass
	else:
		for odate in oload.keys():
			if odate == "storename": 
				continue
			odatetime = datetime.strptime(odate, '%Y年%m月%d日').date()
			if odatetime < date.today(): 
				continue
			try:
				newSpecial = specialHours[odate]
			except KeyError:
				storeDiff += " " * 8 + "{}：取消 {}\n".format(odate, oload[odate]["special"])
				logging.info("Apple {} {} 取消 {}".format(sn, odate, olad[odate]["special"]))

	if len(storeDiff):
		comparison += "    Apple {}\n{}".format(sn, storeDiff)

os.rename("Retail/storeHours.json", "Retail/storeHours-" + runtime + ".json")

logging.info("写入新的 storeHours.json")
jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
with open("Retail/storeHours.json", "w") as w:
	w.write(jOut)

if len(comparison):
	tOut = "Apple Store 特别营业时间\n生成于 {}\n\n变化：\n{}\n原始 JSON:\n{}".format(runtime, comparison, jOut)
	fileDiff = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>specialHours</title>
</head>

<body><pre><code>
{}
</code></pre></body></html>
""".format(tOut)
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