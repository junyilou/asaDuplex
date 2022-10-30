import os
import sys
import json
import logging
import asyncio
from base64 import b64encode
from datetime import datetime, date, UTC

from bot import chat_ids
from storeInfo import storeInfo, actualName, dieterURL, DieterHeader, nsoString
from modules.constants import userAgent
from modules.util import request, disMarkdown, setLogger, session_func
from sdk_aliyun import async_post

specialist = []
INVALIDDATE = datetime(2001, 5, 19)
INVALIDREMOTE = [date(2021, 7, 13), date(2021, 8, 28), date(2021, 8, 29), date(2022, 1, 7)]

with open("storeInfo.json") as s:
	storejson = json.loads(s.read())

async def down(session, rtl, isSpecial, semaphore = None):
	global specialist
	rtl = f"{rtl:0>3}"
	
	try: 
		saved = storejson['last'][rtl]
		savedDatetime = datetime.strptime(saved, "%d %b %Y %H:%M:%S")
	except KeyError:
		saved = None
		savedDatetime = None
	try:
		if semaphore != None:
			await semaphore.acquire()
		if rtl.endswith("00"):
			logging.info(f"开始下载 R{rtl}")
		remote = await DieterHeader(rtl = rtl, session = session)
		remoteDatetime = datetime.strptime(remote, "%d %b %Y %H:%M:%S")
	except TypeError:
		remoteDatetime = None
	finally:
		if semaphore != None:
			semaphore.release()

	if not remoteDatetime:
		if isSpecial:
			logging.info(f"R{rtl} 文件不存在或获取失败")
		return False
	elif not savedDatetime:
		savedDatetime = INVALIDDATE

	if remoteDatetime > savedDatetime:
		if remoteDatetime.date() in INVALIDREMOTE:
			logging.info(f"R{rtl} 找到了更佳的远端无效时间")
			storejson['last'][rtl] = remote
			storejson['update'] = datetime.now(UTC).strftime("%F %T GMT")
			return True

		logging.info(f"R{rtl} 更新，标签为 {remote}")
		savename = f"Retail/R{rtl}_{remote.replace(' ', '').replace(':', '')}.png"

		try:
			r = await request(session = session, url = dieterURL(rtl), headers = userAgent, 
				ssl = False, mode = "raw", ensureAns = False)
			with open(savename, "wb") as w:
				w.write(r)
		except:
			logging.error(f"下载文件到 {savename} 失败")
			pass

		sif = storeInfo(rtl)
		name = actualName(sif["name"])
		info = [f"*{sif['flag']} Apple {name}* (R{rtl})", "", f"*远程标签* {remote}"]
		if "nso" in sif:
			info.insert(1, nsoString(sif = sif))
		if saved:
			info.insert(-1, f"*本地标签* {saved}")
		info = "\n".join(info)
	
		if isSpecial: 
			logging.info("正在更新 specialist.txt")
			specialist.remove(str(int(rtl)))
			with open("Retail/specialist.txt", "w") as w:
				w.write(", ".join(specialist))

		storejson['last'][rtl] = remote
		if savedDatetime == INVALIDDATE:
			storejson["last"] = dict(sorted(storejson["last"].items(), key = lambda k: k[0]))

		storejson['update'] = datetime.now(UTC).strftime("%F %T GMT")

		with open(savename, "rb") as r:
			img = b64encode(r.read()).decode()
		push = {
			"chat_id": chat_ids[0],
			"mode": "photo-text",
			"image": "BASE64" + img,
			"text": disMarkdown(f'*来自 Rtl 的通知*\n\n{info}'),
			"parse": "MARK"
		}
		await async_post(push)

		return True

	elif isSpecial:
		logging.info(f"R{rtl} 图片没有更新")
	return False

@session_func
async def main(session):
	global specialist
	semaphore = asyncio.Semaphore(50)

	match sys.argv:
		case [_]:
			print("请指定一种运行模式: normal, special 或 single")
			return
		case [_, "normal"]:
			setLogger(logging.INFO, os.path.basename(__file__))
			logging.info("开始枚举零售店")
				
			runFlag = False
			tasks = [down(session, f"{j:0>3d}", False, semaphore) for j in range(1, 901)]
			runFlag |= any(await asyncio.gather(*tasks))

		case [_, "special"]:
			with open("Retail/specialist.txt") as l:
				specialist = eval(f"[{l.read()}]")
			specialist = [str(i) for i in specialist]

			if len(specialist):
				setLogger(logging.INFO, os.path.basename(__file__))
				logging.info("开始特别观察模式: " + ", ".join(specialist))

				tasks = [down(session, i, True, semaphore) for i in specialist]
				runFlag = any(await asyncio.gather(*tasks))
			else:
				return

		case [_, "single", *targets]:
			setLogger(logging.INFO, os.path.basename(__file__))
			logging.info("开始单独调用模式: " + ", ".join(targets))
			tasks = [down(session, i, False, semaphore) for i in targets]
			runFlag = any(await asyncio.gather(*tasks))

		case [_, mode, *_]:
			print("指定了错误的运行模式: normal, special 或 single")
			return

	if runFlag:
		logging.info("正在更新 storeInfo.json")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open("storeInfo.json", "w") as sw:
			sw.write(sOut)

asyncio.run(main())
logging.info("程序结束")