import json
import os
import logging
from sys import stdout
from datetime import datetime, date

from storeInfo import *
from modules.special import speHours
from modules.constants import setLogger, DIFFhead, DIFFfoot
from sdk_aliyun import post
from bot import chat_ids

printDebug = True
from sys import argv
if "silent" in argv[1:]:
	printDebug = False
	argv.remove("silent")
if len(argv[1:]):
	include = " ".join(argv[1:])
	exclude = ""
else:
	include = "🇨🇳"
	exclude = "大连恒隆广场"

stores = storeReturn(include, remove_close = True, remove_future = True)
excludeStores = storeReturn(exclude, remove_close = True, remove_future = True)
stores = [i for i in stores if i not in excludeStores]

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")

today = date.today()
runtime = str(today)
comparison = ""
diffStore = []
calendar = {}

try: 
	with open("Retail/storeHours.json") as o:
		orgjson = json.loads(o.read())
except FileNotFoundError: 
	orgjson = {}
	with open("Retail/storeHours.json", "w") as w:
		w.write("{}")

allSpecial = {**orgjson, "created": runtime}

for sid, sn in stores:
	if printDebug:
		cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 40)
		print(f"[{'':=^{perc}}{'':^{40 - perc}}] R{sid} {cur}/{tot} {cur / tot:.1%}", end = "\r")
		stdout.flush()

	specialHours = speHours(sid)
	storeDiff = ""

	if len(specialHours):
		allSpecial[sid] = {"storename": sn, **allSpecial.get(sid, {}), **specialHours}

	for s in specialHours:
		fSpecial = specialHours[s]["special"]
		if s in calendar:
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

	if sid in orgjson:
		for odate in list(orgjson[sid]):
			if odate == "storename": 
				continue
			odatetime = datetime.strptime(odate, '%Y-%m-%d').date()
			if odatetime < today: 
				continue
			try:
				newSpecial = specialHours[odate]
			except KeyError:
				storeDiff += f"{'':^8}{odate}：取消 {orgjson[sid][odate]['special']}\n"
				allSpecial[sid].pop(odate)

	if len(storeDiff):
		comparison += f"{'':^4}Apple {sn}\n{storeDiff}"
		diffStore.append(sn)

for s in list(allSpecial):
	if s == "created":
		continue
	saved = allSpecial[s]
	for d in list(saved):
		if d == "storename":
			continue
		t = datetime.strptime(d, '%Y-%m-%d').date()
		if t < today:
			allSpecial[s].pop(d)
	if len(saved) == 1:
		allSpecial.pop(s)

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
	with open("/root/html/storeHours.html", "w") as w:
		w.write(fileDiff)
	logging.info("文件生成完成")

	pushStore = "Apple " + "、Apple ".join(diffStore[:2]) + (f" 等 {len(diffStore)} 家零售店" if len(diffStore) > 2 else "")

	push = {
		"mode": "photo-text",
		"chat_id": chat_ids[0], 
		"image": "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_medium_2x.jpg",
		"text": f'*来自 Hours 的通知*\n{pushStore} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)',
		"parse": 'MARK'
	}
	post(push)

else: 
	os.remove(f"Retail/storeHours-{runtime}.json")
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")