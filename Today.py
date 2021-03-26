import os, json, time, logging, requests
from telegram import Bot
from sys import stdout
requests.packages.urllib3.disable_warnings()

from storeInfo import *

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

args = "🇨🇳 🇭🇰 🇲🇴 TW"

pair = storePairs(args.split())
stores = storeReturn(pair)

def disMarkdown(text):
	temp = text
	signs = "\\`_{}[]()#+-.!="
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return temp

appn = ""
with open("Retail/savedEvent.txt") as m: 
	mark = m.read()

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, datefmt = '%T')
logging.info("程序启动")

masterJSON = {}

for sid, sn in stores:
	try:
		slug = storeURL(sid)
		flag = slug.split("https://www.apple.com")[1].split("/retail/")[0]
		website = slug.split("/retail/")[1]
		url = f"https://www.apple.com/today-bff/landing/store?stageRootPath={flag}&storeSlug={website}"
	except IndexError:
		logging.error(f"未能匹配到 R{sid} 的零售店官网页面地址")
		continue

	cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 40)
	print(f"[{'':=^{perc}}{'':^{40 - perc}}] R{sid} {cur}/{tot} {cur / tot:.1%}", end = "\r")
	stdout.flush()
	logging.info(f"访问 Apple {sn} 的零售店官网页面")
	r = requests.get(url, verify = False, headers = userAgent)
	masterJSON[sid] = json.loads(r.text.replace("\u2060", ""))["courses"]

for f in masterJSON:
	fStore = masterJSON[f]
	for fID in fStore:
		fCourse = fStore[fID]
		fName = fCourse["name"].replace("\n", "")
		if (not fName in mark) and (not fName in appn):
			appn += f"{fName},\n"
			stores = storeInfo(f)["name"]
			logging.info(f"在 {stores} 找到新活动 {fName}")
			for j in masterJSON:
				jStore = masterJSON[j]
				if jStore == fStore:
					continue
				for jID in jStore:
					jCourse = jStore[jID]
					if (jCourse["name"].replace("\n", "") == fName):
						jName = storeInfo(j)["name"]
						logging.info(f"在 {jName} 找到相同新活动")
						stores += f"、{jName}"
						break
			push = f"#TodayatApple {fName}\n@ {stores}\n\n{fCourse['mediumDescription']}"
			push = push.replace('"', "").replace("'", "").replace("：", " - ").replace("_", "\_")
			logging.info("输出: " + push.replace("\n", " "))
			photoURL = fCourse["backgroundMedia"]["images"][0]["landscape"]["source"]
			photoURL += "?output-format=jpg&output-quality=80&resize=2880:*"

			logging.getLogger().setLevel(logging.DEBUG)
			bot = Bot(token = token)
			try:
				bot.send_photo(
					chat_id = chat_id, 
					photo = photoURL,
					caption = disMarkdown(push),
					parse_mode = 'MarkdownV2')
			except:
				logging.error("未能成功发送带有图片的消息")
				bot.send_message(
					chat_id = chat_id,
					text = disMarkdown(f'{push}\n\n{photoURL}'),
					parse_mode = 'MarkdownV2')
			logging.getLogger().setLevel(logging.INFO)

if appn != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(mark + appn)

logging.info("程序结束")