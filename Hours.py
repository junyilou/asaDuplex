import os
import asyncio
import json
import logging
from datetime import datetime

from storeInfo import storeReturn, Store
from modules.util import session_func, setLogger, sortOD
from modules.special import speHours, comment
from modules.constants import DIFFHTML
from botpost import async_post
from bot import chat_ids

INCLUDE = "🇨🇳, 🇯🇵"
EXCLUDE = "609"
WORKFILE = "Retail/storeHours.json"
USERLANG = "ZH"

TODAY = (RUNTIME := datetime.now()).date()
LOGSTRING = {
	"ZH": {
		"START": "程序启动",
		"END": "程序结束",
		"NEW": f"{'':8}{{DATE}} 新增: {{HOURS}}",
		"CHANGE": f"{'':8}{{DATE}} 变更: 由 {{HOURS1}} 改为 {{HOURS2}}",
		"CANCEL": f"{'':8}{{DATE}} 取消: {{HOURS}}",
		"WRITE": "写入新的 storeHours.json",
		"NODIFF": "没有发现 storeHours 文件更新",
		"DIFFGEN": "已生成对比文件 storeHours.html",
		"DIFFCONTENT": "Apple Store 特别营业时间\n生成于 {RUNTIME}\n\n变化:\n{DIFF}\n\n日历:\n{CALENDAR}\n\n原始 JSON:\n{JSON}"
	},
	"EN": {
		"START": "Program Started",
		"END": "Program Ended",
		"NEW": f"{'':8}{{DATE}} New: {{HOURS}}",
		"CHANGE": f"{'':8}{{DATE}} Changed: from {{HOURS1}} to {{HOURS2}}",
		"CANCEL": f"{'':8}{{DATE}} Canceled: {{HOURS}}",
		"WRITE": "Generating new storeHours.json",
		"NODIFF": "No updates found",
		"DIFFGEN": "DIFF storeHours.html generated",
		"DIFFCONTENT": "Apple Store Special Hours\nGenerated {RUNTIME}\n\nChanges:\n{DIFF}\n\nCalendar:\n{CALENDAR}\n\nRaw JSON:\n{JSON}"
	}
}
LANG = LOGSTRING[USERLANG]

async def entry(session, semaphore, store, saved):
	async with semaphore:
		special = await speHours(session = session, sid = store.sid,
			runtime = TODAY, userLang = USERLANG == "ZH")
	if special == []:
		return {"hours": saved, "diff": []}

	diff = []
	hours = saved | {"storename": store.name} | special

	for date in special:
		spe = special[date]["special"]
		if date not in saved:
			diff.append(LANG["NEW"].format(DATE = date, HOURS = spe))
		elif (svd := saved[date]["special"]) != spe:
			diff.append(LANG["CHANGE"].format(DATE = date, HOURS1 = svd, HOURS2 = spe))

	for date in saved:
		if date == "storename":
			continue
		dateobj = datetime.strptime(date, '%Y-%m-%d').date()
		if dateobj < TODAY:
			hours.pop(date)
			continue
		if date not in special:
			hours.pop(date)
			diff.append(LANG["CANCEL"].format(DATE = date, HOURS = saved[date]["special"]))

	if diff:
		logging.info(f"[{store.telename(sid = False)}] " + ", ".join([i.lstrip() for i in diff]))

	return {"hours": hours, "diff": diff}

@session_func
async def main(session):
	args = dict(split = True, remove_closed = True, remove_future = True)
	pref = dict(ensure_ascii = False, indent = 2)

	includes = storeReturn(INCLUDE, **args)
	excludes = storeReturn(EXCLUDE, **args)
	stores = [i for i in includes if i not in excludes]

	if os.path.isfile(WORKFILE):
		with open(WORKFILE) as o:
			saved = json.loads(o.read())
	else:
		saved = {}
		with open(WORKFILE, "w") as w:
			w.write(r"{}")

	semaphore = asyncio.Semaphore(20)
	async with asyncio.TaskGroup() as tg:
		tasks = {store: tg.create_task(
			entry(session, semaphore, store, saved.get(store.sid, {})))
		for store in stores}

	results, calendar = {}, {}
	targets, diffs = [], []

	for store, item in tasks.items():
		result = item.result()
		if len(result["hours"]) > 1:
			results[store] = result["hours"]
		if result["diff"]:
			diffs += [f"{'':4}{store.telename(sid = False)}"] + result["diff"]
			targets.append(store)
		for date in result["hours"]:
			if date == "storename":
				continue
			calendar[date] = calendar.get(date, {})
			calendar[date][store] = result["hours"][date]["special"]

	results = {k.sid if isinstance(k, Store) else k: v for k, v in sortOD(results).items()}
	calendar = {k: {i.name: j for i, j in v.items()} for k, v in sortOD(calendar).items()}

	output = {"update": RUNTIME.strftime("%F %T")} | results
	oldfile = WORKFILE.replace(".json", f"-{RUNTIME:%y%m%d%H%M}.json")
	os.rename(WORKFILE, oldfile)
	logging.info(LANG["WRITE"])
	with open(WORKFILE, "w") as w:
		w.write(json.dumps(output, ensure_ascii = False, indent = 2))

	if not diffs:
		logging.info(LANG["NODIFF"])
		return os.remove(oldfile)

	content = LANG["DIFFCONTENT"].format(RUNTIME = RUNTIME.strftime("%F %T"), DIFF = "\n".join(diffs),
		CALENDAR = json.dumps(calendar, **pref), JSON = json.dumps(output, **pref))
	with open("html/storeHours.html", "w") as w:
		w.write(DIFFHTML.format(DIFFTITLE = "Special Hours", DIFFCONTENT = content))
	logging.info(LANG["DIFFGEN"])

	text = ", ".join([i.telename(sid = False) for i in targets])
	push = {
		"mode": "photo-text",
		"chat_id": chat_ids[0],
		"image": targets[0].dieter.split("?")[0],
		"text": f'*来自 Hours 的通知*\n{text} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)',
		"parse": "MARK"
	}
	await async_post(push)

setLogger(logging.INFO, os.path.basename(__file__))
logging.info(LANG["START"])
asyncio.run(main())
logging.info(LANG["END"])