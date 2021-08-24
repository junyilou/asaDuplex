import re
import requests
import json
import logging
import os
from datetime import datetime
requests.packages.urllib3.disable_warnings()

from storeInfo import *
from modules.constants import userAgent, dayOfWeekCHN, disMarkdown, setLogger
from bot import chat_ids
from sdk_aliyun import post

args = ".cn /hk /mo /tw" # Use /us for US

storePattern = "R[0-9]{3}"
cseidPattern = "6[0-9]{18}"

sitemapAppend = eventAppend = ""
seen = []; master = []
with open("Retail/savedEvent.txt") as m: 
	savedID = m.read()
with open("Retail/savedSitemap.txt") as m: 
	savedID += m.read()

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")
runtime = datetime.now().date()

parts = []
for region in args.split(" "):
	region = region.replace("/us", "")
	logging.info(f"正请求 apple.com{region} 的 sitemap 数据")
	r = requests.get(f"https://www.apple.com{region}/today/sitemap.xml", headers = userAgent)
	pattern = re.compile(f"(([a-zA-Z]+-)+([a-zA-Z]+-[0-9]{{6}})(/{cseidPattern}/\?sn={storePattern})?)")
	parts += sorted([(i[0], region) for i in pattern.findall(r.text)], key = lambda k: k[0])

def validDates(ex):
	v = []
	for pattern in ["%y%m%d", "%d%m%y", "%m%d%y"]:
		try:
			date = datetime.strptime(ex, pattern).date()
		except ValueError:
			pass
		else:
			o = [date, abs((date - runtime).days)]
			if date.year in [2020, 2021, 2022] and o not in v:
				v.append(o)
	return v

allPart = " ".join([i[0] for i in parts])
logging.info(f"找到 {len(parts)} 个活动 slug")

for slug, region in parts:
	if slug not in seen:
		pattern = re.compile(f"({slug}(/{cseidPattern}/\?sn={storePattern}))")
		idparts = pattern.findall(allPart)

		try:
			if len(idparts):
				seen.append(idparts[0][0])
				courseID = re.search(cseidPattern, idparts[0][1]).group()
				storeID = re.search(storePattern, idparts[0][1]).group()
			else:
				r = requests.get(f"https://www.apple.com{region}/today/event/{slug}", headers = userAgent)
				courseID = re.search(cseidPattern, r.text).group()
				storeID = None
		except AttributeError:
			courseID = ""
			storeID = None

		if courseID not in savedID:
			logging.info(f"找到新活动 {courseID} {slug} 零售店 {region}/{storeID}")
			master.append([slug, region, courseID, storeID])

for slug, region, courseID, storeID in master:
	logging.info(f"处理活动 {courseID} {slug}")
	uRegion = ("/" + region[1:]) if region else ""
	
	try:
		if not storeID:
			raise Exception
		url = f"https://www.apple.com/today-bff/session/schedule?stageRootPath={uRegion}&courseSlug={slug}&scheduleId={courseID}&sn={storeID}"
		r = requests.get(url, headers = userAgent)
		if r.text == "Unknown request":
			raise Exception
	except:
		url = f"https://www.apple.com/today-bff/session/course?stageRootPath={uRegion}&courseSlug={slug}"
		r = requests.get(url, headers = userAgent)

	_store = json.loads(r.text.replace("\u2060", "").replace("\u00A0", " ").replace("\\n", ""))

	course = _store["courses"][courseID]
	courseName = course["name"]

	sitemapAppend += f"{courseID} {courseName}\n"
	if storeID:
		eventAppend += f"{courseID} {courseName}\n"

	courseStore = actualName(storeInfo(storeID)["name"]) if storeID else "尚无已排课零售店"
	courseStore = "线上活动" if "VIRTUAL" in course["type"] else courseStore
	specialPrefix = f"{course['collectionName']} 系列活动\n" if course['collectionName'] else ''

	if _store["schedules"]:
		timing = _store["schedules"][courseID]["displayDate"][0]["dateTime"]
		sessionURL = f"https://www.apple.com{region}/today/event/{slug}/{courseID}/?sn={storeID}"
		keyboard = [[["预约课程", sessionURL]]]
	else:
		date = re.search("[0-9]{6}", slug).group()
		valid = validDates(date)
		timing = " (或) ".join([(i[0].strftime("%-m 月 %-d 日 ") + dayOfWeekCHN[i[0].weekday()].replace("周", "星期")) for i in valid if i[1] < 45])
		sessionURL = f"https://www.apple.com{region}/today/event/{slug}"
		keyboard = [[["查看课程详情", sessionURL]]]

	text = f"""#TodayatApple #Sitemap 新活动\n
{specialPrefix}*{courseName}*\n
🗺️ {courseStore}
🕘 {timing}\n
*课程简介*
{course['longDescription']}

*课程号* {courseID}""".replace('"', "").replace("'", "")
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
	break

if sitemapAppend:
	logging.info("正在更新 savedSitemap 文件")
	with open("Retail/savedSitemap.txt", "w") as m:
		m.write(savedID + sitemapAppend)
	if eventAppend:
		logging.info("正在更新 savedSitemap 文件")
		with open("Retail/savedEvent.txt", "a") as m:
			m.write(eventAppend)

logging.info("程序结束")