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
TODAY = (RUNTIME := datetime.now()).date()

def sortOD(od):
	res = OrderedDict()
	for k, v in sorted(od.items()):
		res[k] = sortOD(v) if isinstance(v, dict) else v
	return res

async def entry(session, semaphore, sid, sn, saved):
	async with semaphore:
		special = await speHours(session = session, sid = sid, runtime = TODAY, askComment = False)
	
	diff = []
	hours = saved | {"storename": sn} | special

	for date in special:
		if date not in saved:
			diff.append(f"{'':8}{date}: 新增 {special[date]['special']}")
		elif (svd := saved[date]["special"]) != (spe := special[date]["special"]):
			diff.append(f"{'':8}{date}: 由 {svd} 改为 {spe}")

	for date in list(saved):
		if date == "storename":
			continue
		dateobj = datetime.strptime(date, '%Y-%m-%d').date()
		if dateobj < TODAY:
			hours.pop(date)
			continue
		if date not in special:
			diff.append(f"{'':8}{date}: 取消 {saved[date]['special']}")

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
	workfile = "Retail/storeHours.json"

	if os.path.isfile(workfile):
		with open(workfile) as o:
			saved = json.loads(o.read())
	else:
		saved = {}
		with open(workfile, "w") as w:
			w.write(r"{}")

	semaphore = asyncio.Semaphore(20)
	async with asyncio.TaskGroup() as tg:
		tasks = {store: tg.create_task(
			entry(session, semaphore, *store, saved.get(store[0], {})))
		for store in stores}

	results, calendar = {}, {}
	diffs, targets = [], []
	comments = saved.get("comments", {})

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
			comments[cid] = {d: k for d, k in comments.get(cid, {}).items() if datetime.strptime(d, '%Y-%m-%d').date() >= TODAY}
			comments[cid] |= {datetime.strftime(d, '%Y-%m-%d'): k for d, k in comm[cid].items()}
			_ = comm_store.remove(cid) if cid in comm_store else None

	results, calendar, comments = map(sortOD, [results, calendar, comments])
	output = {"update": RUNTIME.strftime("%F %T")} | results | {"comments": comments}
	oldfile = workfile.replace(".json", f"-{RUNTIME.strftime('%y%m%d%H%M')}.json")
	os.rename(workfile, oldfile)
	logging.info("写入新的 storeHours.json")
	with open(workfile, "w") as w:
		w.write(json.dumps(output, ensure_ascii = False, indent = 2))

	if not diffs:
		logging.info("没有发现 storeHours 文件更新")
		return os.remove(oldfile)

	content = "Apple Store 特别营业时间\n生成于 {RUNTIME}\n\n变化:\n{DIFF}\n\n日历:\n{CALENDAR}\n\n原始 JSON:\n{JSON}".format(
		RUNTIME = RUNTIME.strftime("%F %T"), DIFF = "\n".join(diffs),
		CALENDAR = json.dumps(calendar, **pref), JSON = json.dumps(output, **pref))
	with open("html/storeHours.html", "w") as w:
		w.write(DIFFHTML.format(DIFFTITLE = "Special Hours", DIFFCONTENT = content))
	logging.info("已生成对比文件 storeHours.html")

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