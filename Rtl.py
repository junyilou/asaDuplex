import asyncio
import json
import logging
import os
import sys
from base64 import b64encode
from datetime import datetime, date, UTC

from bot import chat_ids
from botpost import async_post
from modules.constants import userAgent
from modules.util import SemaphoreType, SessionType, disMarkdown, request, session_func, setLogger
from storeInfo import DEFAULTFILE, Store, StoreDict, getStore, sidify

DUMMYDICT: StoreDict = {"name": "Store", "flag": "🇺🇸", "state": "California", "city": "Cupertino"}
INVALIDDATE = datetime(2001, 5, 19)
INVALIDREMOTE = [date(2021, 7, 13), date(2021, 8, 28), date(2021, 8, 29), date(2022, 1, 7)]

async def down(session: SessionType, semaphore: SemaphoreType, sid: str,
	storejson: dict, specialist: list[str]) -> bool:
	try:
		store = getStore(sid)
		assert store is not None
	except AssertionError:
		logging.warning(f"请求搜索 {sid} 零售店数据不存在")
		store = Store(sid = sidify(sid), dct = DUMMYDICT)
	saved = savedDatetime = None
	if hasattr(store, "modified"):
		saved = store.modified
		savedDatetime = datetime.strptime(saved, "%d %b %Y %H:%M:%S")
	try:
		async with semaphore:
			remote = await store.header(session = session)
		assert isinstance(remote, str)
		remoteDatetime = datetime.strptime(remote, "%d %b %Y %H:%M:%S")
	except:
		remote, remoteDatetime = "", None

	if not remoteDatetime:
		if specialist != []:
			logging.info(f"{store.rid} 文件不存在或获取失败")
		return False
	elif not savedDatetime:
		savedDatetime = INVALIDDATE

	if remoteDatetime > savedDatetime:
		storejson[store.sid]["modified"] = remote
		storejson[store.sid] = dict(sorted(storejson[store.sid].items()))
		if remoteDatetime.date() in INVALIDREMOTE:
			logging.info(f"{store.rid} 找到了更佳的远端无效时间")
			return True

		logging.info(f"{store.rid} 更新，标签为 {remote}")
		savename = f"Retail/{store.rid}_{remote.replace(' ', '').replace(':', '')}.png"

		try:
			r = await request(session = session, url = store.dieter, headers = userAgent,
				ssl = False, mode = "raw", ensureAns = False)
			with open(savename, "wb") as w:
				w.write(r)
			img = "BASE64" + b64encode(r).decode()
		except:
			logging.error(f"下载文件到 {savename} 失败")
			img = store.dieter

		info = [store.telename(flag = True, bold = True, sid = True), "", f"*远程标签* {remote}"]
		if hasattr(store, "dates"):
			info.insert(1, store.nsoString())
		if saved:
			info.insert(-1, f"*本地标签* {saved}")
		info = "\n".join(info)

		if specialist != []:
			toPop = str(store.iid)
			_ = specialist.remove(toPop) if toPop in specialist else None

		push = {
			"chat_id": chat_ids[0],
			"mode": "photo-text",
			"image": img,
			"text": disMarkdown(f'*来自 Rtl 的通知*\n\n{info}'),
			"parse": "MARK"}
		await async_post(push)
		return True
	elif specialist != []:
		logging.info(f"{store.rid} 图片没有更新")
	return False

@session_func
async def main(session: SessionType):
	semaphore = asyncio.Semaphore(50)
	with open(DEFAULTFILE) as r:
		storejson = json.load(r)

	match sys.argv[1:]:
		case []:
			return print("请指定一种运行模式: normal, special 或 single")
		case ["normal" | "single" as mode, *targets]:
			setLogger(logging.INFO, os.path.basename(__file__))
			if mode == "normal":
				targets = [i for i in storejson if i != "update"]
			logging.info(f"开始查询 {len(targets)} 家零售店")
			tasks = [down(session, semaphore, i, storejson, []) for i in targets]
			runFlag = any(await asyncio.gather(*tasks))
		case ["special"]:
			with open("Retail/specialist.txt") as r:
				specialist = eval(f"[{r.read()}]")
			specialist = [str(i) for i in specialist]
			locallist = specialist.copy()
			if not len(specialist):
				return
			setLogger(logging.INFO, os.path.basename(__file__))
			logging.info("开始特别观察模式: " + ", ".join(specialist))
			tasks = [down(session, semaphore, i, storejson, specialist) for i in locallist]
			runFlag = any(await asyncio.gather(*tasks))
			if locallist != specialist:
				logging.info("正在更新特别观察列表")
				with open("Retail/specialist.txt", "w") as w:
					w.write(str(list(map(int, specialist))).strip("[]"))
		case _:
			return print("指定了错误的运行模式: normal, special 或 single")

	if runFlag:
		logging.info(f"正在更新 {DEFAULTFILE}")
		storejson["update"] = datetime.now(UTC).strftime("%F %T GMT")
		with open(DEFAULTFILE, "w") as w:
			json.dump(storejson, w, ensure_ascii = False, indent = 2)
	logging.info("程序结束")

asyncio.run(main())