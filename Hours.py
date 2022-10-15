import json
import os
import logging
import asyncio
from datetime import datetime, date

from storeInfo import *
from modules.special import speHours
from modules.constants import DIFFHTML
from modules.util import setLogger, session_func
from sdk_aliyun import async_post
from bot import chat_ids

stdout = lambda p: print(datetime.now().strftime("[%F %T] ") + p)
from sys import argv
if "logging" in argv:
	stdout = logging.info
	argv.remove("logging")
if len(argv) > 1:
	include, exclude = " ".join(argv[1:]), ""
else:
	include, exclude = "🇨🇳", ""

today = date.today()
runtime = str(today)
comparison = ""
diffStore = []
calendar = {}

async def entry(session, sid, sn):
	global orgjson, allSpecial, comparison, diffStore, calendar
	specialHours = await speHours(session, sid)
	stdout(f"处理 Apple {sn} (R{sid})")
	storeDiff = ""

	if len(specialHours):
		allSpecial[sid] = {"storename": sn} | allSpecial.get(sid, {}) | specialHours

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
		comp = f"{'':^4}Apple {sn}\n{storeDiff}"
		comparison += comp
		stdout(comp.strip())
		diffStore.append(sn)

@session_func
async def main(session):
	global orgjson, allSpecial, comparison, diffStore, calendar

	stores = storeReturn(include, needSplit = True, remove_closed = True, remove_future = True)
	excludeStores = storeReturn(exclude, needSplit = True, remove_closed = True, remove_future = True)
	stores = [i for i in stores if i not in excludeStores]

	try: 
		with open("Retail/storeHours.json") as o:
			orgjson = json.loads(o.read())
	except FileNotFoundError: 
		orgjson = {}
		with open("Retail/storeHours.json", "w") as w:
			w.write(r"{}")

	allSpecial = orgjson | {"created": runtime}
	tasks = [entry(session, sid, sn) for sid, sn in stores]
	await asyncio.gather(*tasks)

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

	stdout("写入新的 storeHours.json")
	jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
	calendar = dict(sorted(calendar.items(), key = lambda k: k[0]))
	calendar = json.dumps(calendar, ensure_ascii = False, indent = 2)
	with open("Retail/storeHours.json", "w") as w:
		w.write(jOut)

	if len(comparison):
		title = "Special Hours"
		content = f"Apple Store 特别营业时间\n生成于 {runtime}\n\n\n变化:\n{comparison}\n\n日历:\n{calendar}\n\n\n原始 JSON:\n{jOut}"
		pushStore = "Apple " + "、Apple ".join(diffStore[:2]) + (f" 等 {lendiff} 家零售店" if (lendiff := len(diffStore)) > 2 else "")

		with open("/home/ecs-user/html/storeHours.html", "w") as w:
			w.write(DIFFHTML.format(DIFFTITLE = title, DIFFCONTENT = content))
		stdout("已生成对比文件 storeHours.html")

		push = {
			"mode": "photo-text",
			"chat_id": chat_ids[0], 
			"image": "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_medium_2x.jpg",
			"text": f'*来自 Hours 的通知*\n{pushStore} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)',
			"parse": 'MARK'
		}
		await async_post(push, logger = stdout)

	else: 
		os.remove(f"Retail/storeHours-{runtime}.json")
		stdout("没有发现 storeHours 文件更新")

setLogger(logging.INFO, os.path.basename(__file__))
stdout("程序启动")
asyncio.run(main())
stdout("程序结束")