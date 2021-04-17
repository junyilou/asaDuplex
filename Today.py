import os, json, time, logging, requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from sys import stdout
requests.packages.urllib3.disable_warnings()

from storeInfo import *

from bot import tokens, chat_ids
token = tokens[2]; chat_id = chat_ids[0]

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
			
			specialSuffix = "（线上）" if "VIRTUAL" in course["type"] else ''
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
			else:
				sortTime = sorted(availableTime, key = lambda k: k[1])[0]
				if len(availableStore) == 1:
					if len(availableTime) == 1:
						timing = sortTime[0]
					else:
						timing = f"{sortTime[0]} 起，共 {len(availableTime)} 次排课"
				else:
					timing = f"{sortTime[0]} 于 Apple {actualName(storeInfo(sortTime[2])['name'])} 起，共 {len(availableTime)} 次排课"

				sessionURL = f"{storeURL(sortTime[2]).split('/retail')[0]}/today/event/{course['urlTitle']}/{sortTime[3]}/?sn=R{sortTime[2]}"
				keyboard = [[InlineKeyboardButton("预约课程", url = sessionURL)]]

				logging.info(f"找到此活动的课程时间 {timing}")
				logging.info(f"最终课程信息：课程 ID {courseID}，课次 ID {courseID if not len(availableTime) else sortTime[3]}")

			push = f"""#TodayatApple 新活动\n
{specialPrefix}*{courseName}*{specialSuffix}\n
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