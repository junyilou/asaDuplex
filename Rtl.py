import os
import sys
import json
import logging
import requests
import time
from datetime import datetime, timezone, date
requests.packages.urllib3.disable_warnings()

from storeInfo import DieterInfo, DieterHeader
from modules.constants import disMarkdown, setLogger, userAgent, dieterURL

from telegram import Bot
from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

def down(rtl, isSpecial):
	rtl = f"{rtl:0>3}"
	
	try: 
		saved = storejson['last'][rtl]
		savedDatetime = datetime.strptime(saved, "%d %b %Y %H:%M:%S")
	except KeyError: 
		savedDatetime = None
	try:
		remote = DieterHeader(rtl)
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

		photoURL = dieterURL(rtl)
		r = requests.get(photoURL, headers = userAgent, verify = False)
		with open(savename, "wb") as w:
			w.write(r.content)

		tellRaw = DieterInfo(rtl)
		tellRaw = tellRaw.replace("#图片更新 #标签 ", "").replace(", 首次开幕于", ",\n*首次开幕于*") + f"\n*修改标签* {remote}" 
		
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
				caption = disMarkdown(f'*来自 Rtl 的通知*\n{tellRaw}'),
				parse_mode = 'MarkdownV2'
			)
		except:
			bot.send_photo(
				chat_id = chat_id, 
				photo = photoURL,
				caption = disMarkdown(f'*来自 Rtl 的通知*\n{tellRaw}'),
				parse_mode = 'MarkdownV2'
			)
		return True

	elif isSpecial:
		logging.info(f"R{rtl} 图片没有更新")
	return False

totalStore = 901
with open("storeInfo.json") as s:
	storejson = json.loads(s.read())

if len(sys.argv) == 1:
	print("请指定一种运行模式: normal, special 或 single")
	exit()

writeFlag = False

if sys.argv[1] == "normal":
	setLogger(logging.INFO, os.path.basename(__file__))
	logging.info("开始枚举零售店")
	func = logging.info if "silent" in sys.argv else print
	for j in range(1, totalStore):
		runFlag = down(f"{j:0>3d}", False)
		if (not writeFlag) and (runFlag):
			writeFlag = True
		if j % 100 == 0:
			func(f"已完成 {j / 100:.0f}/9")

if sys.argv[1] == "special":
	with open("Retail/specialist.txt") as l:
		specialist = eval(f"[{l.read()}]")
	specialist = [str(i) for i in specialist]
	if len(specialist):
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始特别观察模式: " + ", ".join(specialist))
		for i in specialist:
			runFlag = down(i, True)
			if (not writeFlag) and (runFlag):
				writeFlag = True
	else:
		exit()

if sys.argv[1] == "single":
	setLogger(logging.INFO, os.path.basename(__file__))
	logging.info("开始单独调用模式: " + ", ".join(sys.argv[2:]))
	for i in sys.argv[2:]:
		runFlag = down(i, False)
		if (not writeFlag) and (runFlag):
			writeFlag = True

if writeFlag:
	logging.info("正在更新 storeInfo.json")
	sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
	with open("storeInfo.json", "w") as sw:
		sw.write(sOut)

logging.info("程序结束")