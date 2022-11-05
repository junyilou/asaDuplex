import os
import asyncio
import json
import logging
from datetime import datetime
from collections import OrderedDict

from storeInfo import storeReturn, dieterURL
from modules.util import session_func, setLogger
from modules.special import speHours, comment
from modules.constants import DIFFHTML
from sdk_aliyun import async_post
from bot import chat_ids

INCLUDE = "🇨🇳"
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

def sortOD(od):
	res = OrderedDict()
	for k, v in sorted(od.items()):
		res[k] = sortOD(v) if isinstance(v, dict) else v
	return res

async def entry(session, semaphore, sid, sn, saved):
	async with semaphore:
		special = await speHours(session = session, sid = sid, 
			runtime = TODAY, askComment = False, userLang = USERLANG == "ZH")
	
	diff = []
	hours = saved | {"storename": sn} | special

	for date in special:
		spe = special[date]["special"]
		if date not in saved:
			diff.append(LANG["NEW"].format(DATE = date, HOURS = spe))
		elif (svd := saved[date]["special"]) != spe:
			diff.append(LANG["CHANGE"].format(DATE = date, HOURS1 = svd, HOURS2 = spe))

	for date in list(saved):
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
		logging.info(f"[Apple {sn}] " + ", ".join([i.lstrip() for i in diff]))

	return {"hours": hours, "diff": diff}

@session_func
async def main(session):
	args = dict(needSplit = True, remove_closed = True, remove_future = True)
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
			entry(session, semaphore, *store, saved.get(store[0], {})))
		for store in stores}

	results, calendar = {}, {}
	diffs, targets = [], []
	comments = {i: j for i, j in {sid: {d: k for d, k in saved["comments"][sid].items() if 
		datetime.strptime(d, '%Y-%m-%d').date() >= TODAY} for sid in saved.get("comments", {})}.items() if j}

	for store, item in tasks.items():
		sid, sn = store
		result = item.result()
		if len(result["hours"]) > 1:
			results[sid] = result["hours"]
		if result["diff"]:
			diffs += [f"{'':4}Apple {sn}"] + result["diff"]
			targets.append(store)
		for date in result["hours"]:
			if date == "storename":
				continue
			calendar[date] = calendar.get(date, {})
			calendar[date][sn] = result["hours"][date]["special"]

	comm_store = [i[0] for i in targets]
	while len(comm_store):
		sid = comm_store.pop(0)
		comm = await comment(session, sid)
		for cid in comm:
			comments[cid] = comments.get(cid, {}) | {datetime.strftime(d, '%Y-%m-%d'): k for d, k in comm[cid].items()}
			_ = comm_store.remove(cid) if cid in comm_store else None

	results, calendar, comments = map(sortOD, [results, calendar, comments])
	output = {"update": RUNTIME.strftime("%F %T")} | results | {"comments": comments}
	oldfile = WORKFILE.replace(".json", f"-{RUNTIME.strftime('%y%m%d%H%M')}.json")
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

	text = ", Apple ".join(["", *[i[1] for i in targets]]).removeprefix(", ")
	push = {
		"mode": "photo-text",
		"chat_id": chat_ids[0],
		"image": dieterURL(targets[0][0]).split("?")[0],
		"text": f'*来自 Hours 的通知*\n{text} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)',
		"parse": "MARK"
	}
	await async_post(push)

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")
asyncio.run(main())
logging.info("程序结束")