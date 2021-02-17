import os, sys, json, logging, requests
from telegram import Bot

from dieter import DieterInfo, DieterHeader

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
requests.packages.urllib3.disable_warnings()

userAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15"

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, datefmt = '%T')

def disMarkdown(text):
	temp = text
	signs = "\\`_{}[]()#+-.!="
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return temp

def down(rtl, isSpecial):
	try: 
		rmod = storejson['last'][rtl]
	except KeyError: 
		rmod = ""
	rhed = DieterHeader(rtl)
	if rhed == "404" :
		if isSpecial:
			logging.info(f"检查到 R{rtl} 的图片服务器中不存在")
		return
	if rhed != rmod:
		logging.info(f"监测到 R{rtl} 有更新，正在保存图片")
		savename = f"R{rtl}_{rhed.replace(' ', '').replace(',', '').replace(':', '')}.png"
		photoURL = f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{rtl}.png"

		r = requests.get(photoURL, headers = {'User-Agent': userAgent}, verify = False)
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
		logging.info("正在更新 storeInfo.json")
		sOut = json.dumps(storejson, ensure_ascii = False, indent = 2)
		with open("Retail/storeInfo.json", "w") as sw:
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
with open("Retail/storeInfo.json") as s:
	storejson = json.loads(s.read())

if len(sys.argv) == 1:
	print("请指定一种运行模式: normal, special 或 single")
	logging.info("Rtl 未被指定运行模式")
	logging.info("程序结束")

if sys.argv[1] == "normal":
	logging.info("开始枚举零售店")
	for j in range(1, totalStore):
		down(f"{j:0>3d}", False)
		if j % 100 == 0:
			logging.info(f"已完成 {j / 100:.0f}/9")
	logging.info("程序结束")

if sys.argv[1] == "special":
	with open("Retail/specialist.txt") as l:
		specialist = l.read().replace("\n", "").split(", ")
	try: 
		specialist.remove('')
	except ValueError: 
		pass
	if len(specialist):
		logging.info("开始特别观察模式: " + ", ".join(specialist))
		for i in specialist:
			down(i, True)
		logging.info("程序结束")

if sys.argv[1] == "single":
	logging.info("开始单独调用模式: " + ", ".join(sys.argv[2:]))
	for i in sys.argv[2:]:
		down(i, False)
	logging.info("程序结束")