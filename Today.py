import os, json, time, logging, requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from sys import stdout
requests.packages.urllib3.disable_warnings()

from storeInfo import *

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
from constants import disMarkdown, setLogger

printDebug = True
from sys import argv
if "silent" in argv[1:]:
	printDebug = False
	argv.remove("silent")
if len(argv[1:]):
	args = " ".join(argv[1:])
else:
	args = "🇨🇳 🇭🇰 🇲🇴 TW"

pair = storePairs(args.split())
stores = storeReturn(pair)

append = ""
masterJSON = {}
with open("Retail/savedEvent.txt") as m: 
	savedID = m.read()

setLogger(logging.INFO, os.path.basename(__file__))
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

	if printDebug:
		cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 40)
		print(f"[{'':=^{perc}}{'':^{40 - perc}}] R{sid} {cur}/{tot} {cur / tot:.1%}", end = "\r")
		stdout.flush()
	logging.info(f"访问 Apple {sn} 的零售店官网页面")
	r = requests.get(url, verify = False, headers = userAgent)
	try:
		rj = json.loads(r.text.replace("\u2060", "").replace("\u00A0", " ").replace("\\n", ""))
		masterJSON[sid] = {"courses": rj["courses"], "schedules": rj["schedules"]}
	except json.decoder.JSONDecodeError:
		pass

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
			courseStore = "线上活动" if "VIRTUAL" in course["type"] else courseStore
			
			specialPrefix = f"{course['collectionName']} 系列活动\n" if course['collectionName'] else ''
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
				keyboard = [[InlineKeyboardButton("访问 Apple 主页", url = sessionURL)]]
				logging.error("未找到此课程的排课信息")
			elif "VIRTUAL" in course["type"]:
				setTime = availableTime[0]
				timing = setTime[0]
				sessionURL = f"{storeURL(setTime[2]).split('/retail')[0]}/today/event/{course['urlTitle']}/{setTime[3]}/?sn=R{setTime[2]}"
				keyboard = [[InlineKeyboardButton("预约课程", url = sessionURL)]]

				logging.info(f"找到线上活动的课程时间 {timing}")
				logging.info(f"最终课程信息：课程 ID {courseID}，课次 ID {setTime[3]}")
			else:
				sortTime = sorted(availableTime, key = lambda k: k[1])[0]
				if len(availableStore) == 1:
					if len(availableTime) == 1:
						timing = sortTime[0]
					else:
						timing = f"{sortTime[0]} 起，共 {len(availableTime)} 个排课"
				else:
					timing = f"{sortTime[0]} 于 Apple {actualName(storeInfo(sortTime[2])['name'])} 起，共 {len(availableTime)} 次排课"

				sessionURL = f"{storeURL(sortTime[2]).split('/retail')[0]}/today/event/{course['urlTitle']}/{sortTime[3]}/?sn=R{sortTime[2]}"
				keyboard = [[InlineKeyboardButton("预约课程", url = sessionURL)]]

				logging.info(f"找到此活动的课程时间 {timing}")
				logging.info(f"最终课程信息：课程 ID {courseID}，课次 ID {sortTime[3]}")

			push = f"""#TodayatApple 新活动\n
{specialPrefix}*{courseName}*\n
🗺️ {courseStore}
🕘 {timing}\n
*课程简介*
{course['longDescription']}"""
			push = push.replace('"', "").replace("'", "")
			photoURL = course["backgroundMedia"]["images"][0]["landscape"]["source"]
			photoURL += "?output-quality=80&resize=2880:*"
			keyboard[0].append(InlineKeyboardButton("下载活动配图", url = photoURL))
			reply_markup = InlineKeyboardMarkup(keyboard)

			logging.getLogger().setLevel(logging.DEBUG)
			bot = Bot(token = token)
			try:
				bot.send_photo(
					chat_id = chat_id, photo = photoURL,
					caption = disMarkdown(push),
					parse_mode = 'MarkdownV2',
					reply_markup = reply_markup)
			except:
				logging.error("未能成功发送带有图片的消息")
				bot.send_message(
					chat_id = chat_id, text = disMarkdown(push),
					parse_mode = 'MarkdownV2',
					reply_markup = reply_markup)
			logging.getLogger().setLevel(logging.INFO)

if append != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(savedID + append)

logging.info("程序结束")