import os
import sys
import json
import logging
import asyncio
from base64 import b64encode
from datetime import datetime, date, UTC

from bot import chat_ids
from storeInfo import DEFAULTFILE, StoreID
from modules.constants import userAgent
from modules.util import request, disMarkdown, setLogger, session_func
from sdk_aliyun import async_post

INVALIDDATE = datetime(2001, 5, 19)
INVALIDREMOTE = [date(2021, 7, 13), date(2021, 8, 28), date(2021, 8, 29), date(2022, 1, 7)]

async def down(session, sid, storejson, specialist, semaphore):
	store = StoreID(sid)[0]
	if hasattr(store, "modified"):
		saved = store.modified
		savedDatetime = datetime.strptime(saved, "%d %b %Y %H:%M:%S")
	else:
		saved = savedDatetime = None
	try:
		async with semaphore:
			if store.sid.endswith("00"):
				logging.info(f"开始下载 {store.rid}")
			remote = await store.header(session = session)
		remoteDatetime = datetime.strptime(remote, "%d %b %Y %H:%M:%S")
	except:
		remote = remoteDatetime = None

	if not remoteDatetime:
		if specialist != None:
			logging.info(f"{store.rid} 文件不存在或获取失败")
		return False
	elif not savedDatetime:
		savedDatetime = INVALIDDATE

	if remoteDatetime > savedDatetime:
		storejson[store.sid]["modified"] = remote
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
		except:
			logging.error(f"下载文件到 {savename} 失败")
			pass

		info = [store.telename(flag = True, bold = True, sid = True), "", f"*远程标签* {remote}"]
		if hasattr(store, "dates"):
			info.insert(1, store.nsoString())
		if saved:
			info.insert(-1, f"*本地标签* {saved}")
		info = "\n".join(info)
	
		if specialist != None:
			toPop = str(store.iid)
			_ = specialist.remove(toPop) if toPop in specialist else None

		img = b64encode(r).decode()
		push = {
			"chat_id": chat_ids[0],
			"mode": "photo-text",
			"image": "BASE64" + img,
			"text": disMarkdown(f'*来自 Rtl 的通知*\n\n{info}'),
			"parse": "MARK"
		}
		await async_post(push)
		return True
	elif specialist != None:
		logging.info(f"{store.rid} 图片没有更新")
	return False

@session_func
async def main(session):
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
			tasks = [down(session, i, storejson, None, semaphore) for i in targets]
			runFlag = any(await asyncio.gather(*tasks))
		case ["special"]:
			with open("Retail/specialist.txt") as r:
				specialist = eval(f"[{r.read()}]")
			specialist = [str(i) for i in specialist]
			locallist = specialist.copy()

			if len(specialist):
				setLogger(logging.INFO, os.path.basename(__file__))
				logging.info("开始特别观察模式: " + ", ".join(specialist))
				tasks = [down(session, i, storejson, specialist, semaphore) for i in locallist]
				runFlag = any(await asyncio.gather(*tasks))
				if locallist != specialist:
					logging.info("正在更新特别观察列表")
					with open("Retail/specialist.txt", "w") as w:
						w.write(str(list(map(int, specialist))).strip("[]"))
			else:
				return
		case _:
			return print("指定了错误的运行模式: normal, special 或 single")

	if runFlag:
		logging.info(f"正在更新 {DEFAULTFILE}")
		storejson["update"] = datetime.now(UTC).strftime("%F %T GMT")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open(DEFAULTFILE, "w") as w:
			w.write(sOut)

	logging.info("程序结束")

asyncio.run(main())