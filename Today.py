import os
import json
import time
import logging
import requests
from sys import stdout
requests.packages.urllib3.disable_warnings()

from storeInfo import *
from modules.constants import disMarkdown, setLogger
from bot import chat_ids
from sdk_aliyun import post

printDebug = True
from sys import argv
if "silent" in argv[1:]:
	printDebug = False
	argv.remove("silent")
if len(argv[1:]):
	args = " ".join(argv[1:])
else:
	args = "🇨🇳 🇭🇰 🇲🇴 TW"

stores = storeReturn(args, remove_close = True, remove_future = True)

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
	except:
		logging.error(f"未能匹配到 R{sid} 的零售店官网页面地址")
		continue

	if printDebug:
		cur = stores.index((sid, sn)) + 1; tot = len(stores); perc = int(cur / tot * 40)
		print(f"[{'':=^{perc}}{'':^{40 - perc}}] R{sid} {cur}/{tot} {cur / tot:.1%}", end = "\r")
		stdout.flush()
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

			for j in masterJSON:
				if i == j:
					continue
				__store = masterJSON[j]
				for sameID in __store["courses"]:
					if sameID == courseID:
						availableStore.append(j)
			textStore = stateReplace(availableStore)
			for a in textStore:
				if a.isdigit():
					textStore[textStore.index(a)] = actualName(storeInfo(a)["name"])
			courseStore = "线上活动" if "VIRTUAL" in course["type"] else "、".join(textStore)

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
				keyboard = [[["访问课程页面", sessionURL]]]
				logging.error("未找到此课程的排课信息")
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
				keyboard = [[["预约课程", sessionURL]]]

				logging.info(f"找到此活动的课程时间 {timing}")
				logging.info(f"最终课程信息：课程 ID {courseID}，课次 ID {sortTime[3]}")

			text = f"""#TodayatApple 新活动\n
{specialPrefix}*{courseName}*\n
🗺️ {courseStore}
🕘 {timing}\n
*课程简介*
{course['longDescription']}""".replace('"', "").replace("'", "")
			photoURL = course["backgroundMedia"]["images"][0]["landscape"]["source"]
			photoURL += "?output-quality=80&resize=2880:*"
			keyboard[0].append(["下载活动配图", photoURL])

			push = {
				"mode": "photo-text",
				"text": disMarkdown(text),
				"image": photoURL,
				"parse": "MARK",
				"chat_id": chat_ids[0],
				"keyboard": keyboard
			}
			post(push)

if append:
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(savedID + append)

logging.info("程序结束")