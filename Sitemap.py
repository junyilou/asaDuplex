import re, requests, json, logging, os
from datetime import datetime
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
requests.packages.urllib3.disable_warnings()

from storeInfo import *

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
from constants import (
	userAgent, dayOfWeekCHN, disMarkdown, setLogger
)

args = "/cn /hk /mo /tw" # Use /us for US

storePattern = "R[0-9]{3}"
cseidPattern = "6[0-9]{18}"

append = ""
seen = []; master = []
with open("Retail/savedEvent.txt") as m: 
	savedID = m.read()

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
	if not storeID:
		r = requests.get(f"https://www.apple.com/today-bff/session/course?stageRootPath={uRegion}&courseSlug={slug}")
	else:
		r = requests.get(f"https://www.apple.com/today-bff/session/schedule?stageRootPath={uRegion}&courseSlug={slug}&scheduleId={courseID}&sn={storeID}")
	_store = json.loads(r.text.replace("\u2060", "").replace("\u00A0", " ").replace("\\n", ""))

	course = _store["courses"][courseID]
	courseName = course["name"]
	append += f"{courseID} {courseName}\n"
	courseStore = actualName(storeInfo(storeID)["name"]) if storeID else "尚无已排课零售店"
	courseStore = "线上活动" if "VIRTUAL" in course["type"] else courseStore
	specialPrefix = f"{course['collectionName']} 系列活动\n" if course['collectionName'] else ''

	if _store["schedules"]:
		timing = _store["schedules"][courseID]["displayDate"][0]["dateTime"]
		sessionURL = f"https://www.apple.com{region}/today/event/{slug}/{courseID}/?sn={storeID}"
		keyboard = [[InlineKeyboardButton("预约课程", url = sessionURL)]]
	else:
		date = re.search("[0-9]{6}", slug).group()
		valid = validDates(date)
		timing = " (或) ".join([(i[0].strftime("%-m 月 %-d 日 ") + dayOfWeekCHN[i[0].weekday()].replace("周", "星期")) for i in valid if i[1] < 30])
		sessionURL = f"https://www.apple.com{region}/today/event/{slug}"
		keyboard = [[InlineKeyboardButton("查看课程详情", url = sessionURL)]]

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

	bot = Bot(token = token)
	try:
		bot.send_photo(
			chat_id = chat_id, photo = photoURL,
			caption = disMarkdown(push),
			parse_mode = 'MarkdownV2',
			reply_markup = reply_markup)
	except:
		bot.send_message(
			chat_id = chat_id, text = disMarkdown(push),
			parse_mode = 'MarkdownV2',
			reply_markup = reply_markup)

if append != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(savedID + append)

logging.info("程序结束")