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

append = ""
masterJSON = {}
with open("Retail/savedEvent.txt") as m: 
	savedID = m.read()

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

for sid, sn in stores:
	try:
		slug = storeURL(sid)
		flag = slug.split("https://www.apple.com")[1].split("/retail/")[0].replace(".cn", "/cn")
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
	rj = json.loads(r.text.replace("\u2060", "").replace("\\n", ""))
	masterJSON[sid] = {"courses": rj["courses"], "schedules": rj["schedules"]}

for i in masterJSON:
	_store = masterJSON[i]
	for courseID in _store["courses"]:
		availableStore = [i]
		course = _store["courses"][courseID]
		if not any([courseID in savedID, courseID in append]):
			courseName = course["name"]
			append += f"{courseID} {courseName}\n"
			courseStore = actualName(storeInfo(i)["name"])

			for j in masterJSON:
				if i == j:
					continue
				__store = masterJSON[j]
				for sameID in __store["courses"]:
					if sameID == courseID:
						availableStore.append(j)
						courseStore += f'、{actualName(storeInfo(j)["name"])}'
			if "VIRTUAL" in course["type"]:
				courseName = "[线上活动] " + courseName
			logging.info(f"在 {courseStore} 找到新活动 {courseName} ID {courseID}")

			availableTime = []
			for ___store in availableStore:
				for s in masterJSON[___store]["schedules"]:
					session = masterJSON[___store]["schedules"][s]
					if session["courseId"] == courseID:
						availableTime.append((session["displayDate"][0]["dateTime"], session["startTime"], ___store, s))
			if not len(availableTime):
				timing = "该课程尚无具体时间安排"
				sessionURL = storeURL(i).replace("/retail", "/today")
			else:
				sortTime = sorted(availableTime, key = lambda k: k[1])[0]
				if len(availableStore) == 1:
					if len(availableTime) == 1:
						timing = sortTime[0]
					else:
						timing = f"{sortTime[0]} 起，共 {len(availableTime)} 次排课"
				else:
					timing = f"{sortTime[0]} 于 Apple {actualName(storeInfo(sortTime[2])['name'])} 起，共 {len(availableTime)} 次排课"
				sessionURL = f"{storeURL(i).split('/retail')[0]}/today/event/{course['urlTitle']}/{sortTime[3]}/?sn=R{sortTime[2]}"

				logging.info(f"找到此活动的课程时间 {timing}")
				logging.info(f"找到此活动的链接 {sessionURL}")

			push = f"#TodayatApple *{courseName}*\n\n🗺️ {courseStore}\n🕘 {timing}\n\n*课程简介*\n{course['mediumDescription']}\n\n*预约课程*\n{sessionURL}"
			push = push.replace('"', "").replace("'", "").replace("：", " - ")
			photoURL = course["backgroundMedia"]["images"][0]["landscape"]["source"]
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

if append != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(savedID + append)

logging.info("程序结束")