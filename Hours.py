import json, os, logging
from sys import stdout
from datetime import datetime, date
import telegram

from storeInfo import *
from special import speHours
from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
from constants import (
	setLogger, DIFFhead, DIFFfoot
)

printDebug = True
from sys import argv
if "silent" in argv[1:]:
	printDebug = False
	argv.remove("silent")
if len(argv[1:]):
	args = " ".join(argv[1:])
else:
	args = "🇨🇳"

pair = storePairs(args.split())
stores = storeReturn(pair, remove_close = True)

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")
runtime = str(date.today())

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
	if printDebug:
		cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 40)
		print(f"[{'':=^{perc}}{'':^{40 - perc}}] R{sid} {cur}/{tot} {cur / tot:.1%}", end = "\r")
		stdout.flush()

	specialHours = speHours(sid, storePage(sid))
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
			storeDiff += f"{'':^8}{s}：新增 {fSpecial}\n"
		else: 
			if orgSpecial != fSpecial:
				storeDiff += f"{'':^8}{s}：由 {orgSpecial} 改为 {fSpecial}\n"

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
				storeDiff += f"{'':^8}{odate}：取消 {oload[odate]['special']}\n"

	if len(storeDiff):
		comparison += f"{'':^4}Apple {sn}\n{storeDiff}"

os.rename("Retail/storeHours.json", f"Retail/storeHours-{runtime}.json")

logging.info("写入新的 storeHours.json")
jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
calendar = dict(sorted(calendar.items(), key = lambda k: k[0]))
calendar = json.dumps(calendar, ensure_ascii = False, indent = 2)
with open("Retail/storeHours.json", "w") as w:
	w.write(jOut)

if len(comparison):
	fileDiff = f"""{DIFFhead.replace('DIFF HEAD', 'Special Hours')}Apple Store 特别营业时间
生成于 {runtime}\n\n
变化:\n{comparison}\n
日历:\n{calendar}\n\n
原始 JSON:\n{jOut}
{DIFFfoot}
"""
	with open("/home/centos/www/storeHours.html", "w") as w:
		w.write(fileDiff)
	logging.info("文件生成完成")

	logging.getLogger().setLevel(logging.DEBUG)
	bot = telegram.Bot(token = token)
	bot.send_photo(
		chat_id = chat_id, 
		photo = "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_medium_2x.jpg",
		caption = f'*来自 Hours 的通知*\n{comparison.count("Apple")} 个 Apple Store 有特别营业时间变化 [↗](http://myv.ps/storeHours.html)',
		parse_mode = 'MarkdownV2')
	logging.getLogger().setLevel(logging.INFO)

else: 
	os.remove(f"Retail/storeHours-{runtime}.json")
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")