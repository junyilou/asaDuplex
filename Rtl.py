import os
import sys
import json
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timezone, date

from storeInfo import storeInfo, actualName, DieterHeader
from modules.constants import request as request
from modules.constants import disMarkdown, setLogger, userAgent, dieterURL

from telegram import Bot
from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

with open("storeInfo.json") as s:
	storejson = json.loads(s.read())

def swarp(func):
	async def wrapper():
		async with aiohttp.ClientSession() as session:
			return await func(session = session)
	return wrapper

async def down(session, rtl, isSpecial):
	rtl = f"{rtl:0>3}"
	
	try: 
		saved = storejson['last'][rtl]
		savedDatetime = datetime.strptime(saved, "%d %b %Y %H:%M:%S")
	except KeyError: 
		savedDatetime = None
	try:
		remote = await DieterHeader(session, rtl)
		remoteDatetime = datetime.strptime(remote, "%d %b %Y %H:%M:%S")
	except TypeError:
		remoteDatetime = None

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
				ssl = False, ident = None, mode = "raw")
			if isinstance(r, Exception):
				raise r
			with open(savename, "wb") as w:
				w.write(r)
		except:
			pass

		sif = storeInfo(rtl)
		name = actualName(sif["name"])
		info = f"*{sif['flag']} Apple {name}* (R{rtl})"
		if "nso" in sif:
			info += f'\n首次开幕于 {datetime.strptime(sif["nso"], "%Y-%m-%d").strftime("%Y 年 %-m 月 %-d 日")}'
		info += f"\n*修改标签* {remote}" 
		
		if isSpecial: 
			logging.info("正在更新 specialist.txt")
			specialist.remove(str(int(rtl)))
			with open("Retail/specialist.txt", "w") as w:
				w.write(", ".join(specialist))

		storejson['last'][rtl] = remote
		if savedDatetime == datetime(2001, 5, 19):
			storejson['last'] = dict([(k, storejson['last'][k]) for k in sorted(storejson['last'].keys())])
		storejson['update'] = datetime.now(timezone.utc).strftime("%F %T GMT")

		bot = Bot(token = token)
		try:
			bot.send_photo(
				chat_id = chat_id, 
				photo = open(savename, "rb"),
				caption = disMarkdown(f'*来自 Rtl 的通知*\n{info}'),
				parse_mode = 'MarkdownV2'
			)
		except:
			bot.send_photo(
				chat_id = chat_id, 
				photo = dieterURL(rtl),
				caption = disMarkdown(f'*来自 Rtl 的通知*\n{info}'),
				parse_mode = 'MarkdownV2'
			)
		return True

	elif isSpecial:
		logging.info(f"R{rtl} 图片没有更新")
	return False

@swarp
async def main(session):
	if len(sys.argv) == 1:
		return

	if sys.argv[1] == "normal":
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始枚举零售店")
			
		runFlag = False
		for i in range(9):
			tasks = [down(session, f"{j:0>3d}", False) for j in range(i * 100 + 1, i * 100 + 101)]
			runFlag = any(await asyncio.gather(*tasks)) or runFlag
			logging.info(f"已完成 {i + 1} / 9")

	elif sys.argv[1] == "special":
		with open("Retail/specialist.txt") as l:
			specialist = eval(f"[{l.read()}]")
		specialist = [str(i) for i in specialist]

		if len(specialist):
			setLogger(logging.INFO, os.path.basename(__file__))
			logging.info("开始特别观察模式: " + ", ".join(specialist))

			tasks = [down(session, i, True) for i in specialist]
			runFlag = any(await asyncio.gather(*tasks))
		else:
			return

	elif sys.argv[1] == "single" and len(sys.argv) > 2:
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始单独调用模式: " + ", ".join(sys.argv[2:]))
			
		tasks = [down(session, i, False) for i in sys.argv[2:]]
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