import os
import asyncio
import json
import logging
from datetime import datetime

from storeInfo import storeReturn, storeDict, Order
from modules.util import session_func, setLogger, disMarkdown
from modules.constants import DIFFHTML
from bot import chat_ids
from sdk_aliyun import async_post

INCLUDE = "🇨🇳"
EXCLUDE = ""
WORKFILE = "Retail/bannerMessage.json"
USERLANG = "ZH"

RUNTIME = datetime.now()
LOGSTRING = {
	"ZH": {
		"START": "程序启动",
		"END": "程序结束",
		"NORMAL": "[Apple {STORENAME}] {MESSAGE}",
		"CHANGE": "*Apple {STORENAME}*\n本地: {SAVED}\n远端: {MESSAGE}",
		"FAILED": "[Apple {STORENAME}] 获取消息失败",
		"WRITE": "已写入新的 bannerMessage.json",
		"NODIFF": "没有发现 bannerMessage 文件更新"
	},
	"EN": {
		"START": "Program Started",
		"END": "Program Ended",
		"NORMAL": "[Apple {STORENAME}] {MESSAGE}",
		"CHANGE": "[Apple {STORENAME}]\nPrevious: {SAVED}\nCurrent: {MESSAGE}",
		"FAILED": "[Apple {STORENAME}] Failed to get banner message",
		"WRITE": "\nNew bannerMessage.json generated\n",
		"NODIFF": "No updates found"
	}
}
LANG = LOGSTRING[USERLANG]

async def entry(ses, sem, sid, sn, svd):
	logger = logging.getLogger("R" + sid)
	retry, message, critical = 3, None, None
	while message == None and retry:
		async with sem:
			r = await storeDict(sid = sid, session = ses, mode = "raw")
			message = r.get("message", None)
			retry -= 1
	if message == None:
		critical = LANG["FAILED"].format(STORENAME = sn)
		logger.error(critical)
		return svd, critical
	message = (f"[{title}] " if (title := r['messageTitle']) else "") + message
	logger.debug(LANG["NORMAL"].format(STORENAME = sn, MESSAGE = message))
	if message != svd:
		svd_, message_ = map(lambda s: "[Empty]" if len(s) == 0 else s, [svd, message])
		critical = LANG["CHANGE"].format(STORENAME = sn, SAVED = svd_, MESSAGE = message_)
		logger.info(critical)
	return message, critical

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
			_ = saved.pop("update") if "update" in saved else None
	else:
		saved = {}
		with open(WORKFILE, "w") as w:
			w.write(r"{}")

	semaphore = asyncio.Semaphore(20)
	async with asyncio.TaskGroup() as tg:
		tasks = {store: tg.create_task(
			entry(session, semaphore, *store, saved.get(store[0], "")))
		for store in stores}

	criticals = [i for i in [t.result()[1] for t in tasks.values()] if i]
	results = saved | {s[0]: t.result()[0] for s, t in tasks.items()}
	results = {"update": RUNTIME.strftime("%F %T")} | {a: v for a, v in sorted(results.items(), 
		key = lambda k: Order.index(k[0]) if k[0] in Order else (900 + int(k[0]))) if v}

	if not criticals:
		return logging.info(LANG["NODIFF"])

	oldfile = WORKFILE.replace(".json", f"-{RUNTIME.strftime('%y%m%d%H%M')}.json")
	os.rename(WORKFILE, oldfile)
	with open(WORKFILE, "w") as w:
		w.write(json.dumps(results, ensure_ascii = False, indent = 2))
	logging.info(LANG["WRITE"])

	with open("html/bannerMessage.html", "w") as w:
		w.write(DIFFHTML.format(DIFFTITLE = "Banner Message", DIFFCONTENT = "\n\n".join(criticals)))
	push = {
		"mode": "photo-text",
		"chat_id": chat_ids[0],
		"image": "https://digitalassets-retail.cdn-apple.com/retail-image-server/9ed/cc1/2f8/fca/900/7a8/47d/74c/177/cd0/ce288fd8-cdd3-3264-818f-6dc45542c0cb_3rd_drawer_tower_theatre_03_2x_large_2x.jpg",
		"text": f'*来自 bannerMessage 的通知*\n有 {len(criticals)} 个零售店消息更新 [↗](http://aliy.un/html/bannerMessage.html)',
		"parse": "MARK"
	}
	await async_post(push)

setLogger(logging.INFO, os.path.basename(__file__))
logging.info(LANG["START"])
asyncio.run(main())
logging.info(LANG["END"])