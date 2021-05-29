import os, sys, json, logging, requests, time
from telegram import Bot

from storeInfo import DieterInfo, DieterHeader

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
requests.packages.urllib3.disable_warnings()

from constants import (
	disMarkdown, setLogger, userAgent
)

def down(rtl, isSpecial):
	if type(rtl) == int:
		rtl = f"{rtl:0>3d}"
	try: 
		rmod = storejson['last'][rtl]
	except KeyError: 
		rmod = ""
	rhed = DieterHeader(rtl)
	if rhed == "404":
		if isSpecial:
			logging.info(f"检查到 R{rtl} 的图片服务器中不存在")
		return
	if rhed != rmod:
		logging.info(f"监测到 R{rtl} 有更新，正在保存图片")
		savename = f"R{rtl}_{rhed.replace(' ', '').replace(':', '')}.png"
		photoURL = f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{rtl}.png"

		r = requests.get(photoURL, headers = userAgent, verify = False)
		with open(f"Retail/{savename}", "wb") as w:
			w.write(r.content)

		tellRaw = DieterInfo(rtl)
		tellRaw = tellRaw.replace("#图片更新 #标签 ", "").replace(", 首次开幕于", ",\n*首次开幕于*") + f"\n*修改标签* {rhed}" 
		
		if isSpecial: 
			logging.info("正在更新 specialist.txt")
			specialist.remove(rtl)
			with open("Retail/specialist.txt", "w") as w:
				w.write(", ".join(specialist))
		
		storejson['last'][rtl] = rhed
		storejson['last'] = dict([(k, storejson['last'][k]) for k in sorted(storejson['last'].keys())])
		storejson['update'] = time.strftime("%F %T GMT", time.gmtime())
		logging.info("正在更新 storeInfo.json")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open("storeInfo.json", "w") as sw:
			sw.write(sOut)

		logging.getLogger().setLevel(logging.DEBUG)
		bot = Bot(token = token)
		try:
			bot.send_photo(
				chat_id = chat_id, 
				photo = open(f"Retail/{savename}", "rb"),
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
		logging.getLogger().setLevel(logging.INFO)

	elif isSpecial:
		try: 
			pname = f"Apple {storejson['name'][rtl]} (R{rtl})"
		except KeyError: 
			pname = f"Apple Store (R{rtl})"
		logging.info(f"检查到 {pname} 的图片没有更新")

totalStore = 901
with open("storeInfo.json") as s:
	storejson = json.loads(s.read())

if len(sys.argv) == 1:
	print("请指定一种运行模式: normal, special 或 single")
	exit()

if sys.argv[1] == "normal":
	setLogger(logging.INFO, os.path.basename(__file__))
	logging.info("开始枚举零售店")
	for j in range(1, totalStore):
		down(f"{j:0>3d}", False)
		if j % 100 == 0:
			logging.info(f"已完成 {j / 100:.0f}/9")
	logging.info("程序结束")

if sys.argv[1] == "special":
	with open("Retail/specialist.txt") as l:
		specialist = eval(f"[{l.read()}]")
	specialist = [str(i) for i in specialist]
	if len(specialist):
		setLogger(logging.INFO, os.path.basename(__file__))
		logging.info("开始特别观察模式: " + ", ".join(specialist))
		for i in specialist:
			down(i, True)
		logging.info("程序结束")

if sys.argv[1] == "single":
	setLogger(logging.INFO, os.path.basename(__file__))
	logging.info("开始单独调用模式: " + ", ".join(sys.argv[2:]))
	for i in sys.argv[2:]:
		down(i, False)
	logging.info("程序结束")