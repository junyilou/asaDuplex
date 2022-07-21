import os
import sys
import json
import logging
import asyncio
from base64 import b64encode
from datetime import datetime, timezone, date

from bot import chat_ids
from storeInfo import storeInfo, actualName, dieterURL, DieterHeader
from modules.constants import request, disMarkdown, setLogger, userAgent, session_func
from sdk_aliyun import async_post

specialist = []
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
		savedDatetime = datetime(2001, 5, 19)

	if remoteDatetime > savedDatetime:
		if remoteDatetime.date() in [date(2021, 7, 13), date(2021, 8, 28), date(2021, 8, 29), date(2022, 1, 7)]:
			logging.info(f"R{rtl} 找到了更佳的远端无效时间")
			storejson['last'][rtl] = remote
			storejson['update'] = datetime.now(timezone.utc).strftime("%F %T GMT")
			return True

		logging.info(f"R{rtl} 更新，标签为 {remote}")
		savename = f"Retail/R{rtl}_{remote.replace(' ', '').replace(':', '')}.png"

		try:
			r = await request(session = session, url = dieterURL(rtl), headers = userAgent, 
				ssl = False, ident = None, mode = "raw", ensureAns = False)
			with open(savename, "wb") as w:
				w.write(r)
		except:
			logging.error(f"下载文件到 {savename} 失败")
			pass

		sif = storeInfo(rtl)
		name = actualName(sif["name"])
		info = f"*{sif['flag']} Apple {name}* (R{rtl})"
		if "nso" in sif:
			info += f'\n首次开幕于 {datetime.strptime(sif["nso"], "%Y-%m-%d").strftime("%Y 年 %-m 月 %-d 日")}'
		info += f"\n*修改标签* {remote}"
		if saved:
			info += f"\n*原始标签* {saved}"
		
		if isSpecial: 
			logging.info("正在更新 specialist.txt")
			specialist.remove(str(int(rtl)))
			with open("Retail/specialist.txt", "w") as w:
				w.write(", ".join(specialist))

		storejson['last'][rtl] = remote
		if savedDatetime == datetime(2001, 5, 19):
			storejson['last'] = dict([(k, storejson['last'][k]) for k in sorted(storejson['last'].keys())])
		storejson['update'] = datetime.now(timezone.utc).strftime("%F %T GMT")

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
	if len(sys.argv) == 1:
		print("请指定一种运行模式: normal, special 或 single")
		return

	semaphore = asyncio.Semaphore(50)

	if sys.argv[1] == "normal":
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始枚举零售店")
			
		runFlag = False
		tasks = [down(session, f"{j:0>3d}", False, semaphore) for j in range(1, 901)]
		runFlag = any(await asyncio.gather(*tasks)) or runFlag

	elif sys.argv[1] == "special":
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

	elif sys.argv[1] == "single" and len(sys.argv) > 2:
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始单独调用模式: " + ", ".join(sys.argv[2:]))
			
		tasks = [down(session, i, False, semaphore) for i in sys.argv[2:]]
		runFlag = any(await asyncio.gather(*tasks))

	else:
		print("请指定一种运行模式: normal, special 或 single")
		return

	if runFlag:
		logging.info("正在更新 storeInfo.json")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open("storeInfo.json", "w") as sw:
			sw.write(sOut)

asyncio.run(main())
logging.info("程序结束")