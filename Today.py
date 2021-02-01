import os, json, time, logging, requests
import telegram
requests.packages.urllib3.disable_warnings()

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

from storeInfo import *

args = {'s': ['🇨🇳', '🇭🇰', '🇲🇴', 'TW']}

stores = []
functions = {'r': StoreID, 'n': StoreName, 's': StoreNation}
for f in functions.keys():
	if f in args.keys():
		S = map(functions[f], args[f])
		for _s in list(S):
			for __s in _s:
				if __s[0] not in stores:
					stores.append(__s[0])

nationCode = {
	"🇺🇸": "", "🇨🇳": "cn", "🇬🇧": "uk", "🇨🇦": "ca", "🇦🇺": "au", "🇫🇷": "fr", "🇮🇹": "it",
	"🇩🇪": "de", "🇪🇸": "es", "🇯🇵": "jp", "🇨🇭": "chde", "🇦🇪": "ae", "🇳🇱": "nl", "🇸🇪": "se",
	"🇧🇷": "br", "🇹🇷": "tr", "🇸🇬": "sg", "🇲🇽": "mx", "🇦🇹": "at", "🇧🇪": "befr", "🇰🇷": "kr",
	"🇹🇭": "th", "🇭🇰": "hk", "🇲🇴": "mo", "🇹🇼": "tw"
}

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

for sid in stores:
	try:
		sif = storeInfo(sid)
		region = "" if sif["flag"] == "🇺🇸" else "/" + nationCode[sif["flag"]]
		url = "https://www.apple.com/today-bff/landing/store?stageRootPath={}&storeSlug={}".format(region, sif["website"])
	except KeyError:
		logging.error("未能匹配到 R{} 的零售店官网页面地址".format(sid))
	logging.info("正在访问 R{} 的零售店官网页面".format(sid))
	r = requests.get(url, verify = False)
	masterJSON[sid] = json.loads(r.text.replace("\u2060", ""))["courses"]

for f in masterJSON:
	fStore = masterJSON[f]
	for fID in fStore:
		fCourse = fStore[fID]
		fName = fCourse["name"].replace("\n", "")
		if (not fName in mark) and (not fName in appn):
			appn += fName + ",\n"
			stores = storeInfo(f)["name"]
			logging.info("在{}找到新活动 {}".format(stores, fName))
			for j in masterJSON:
				jStore = masterJSON[j]
				if jStore == fStore:
					continue
				for jID in jStore:
					jCourse = jStore[jID]
					if (jCourse["name"].replace("\n", "") == fName):
						jName = storeInfo(j)["name"]
						logging.info("在{}找到相同新活动".format(jName))
						stores += "、" + jName
						break
			push = "#TodayatApple {}}\n@ {}\n\n".format(fName, stores) + fCourse["mediumDescription"]
			push = push.replace('"', "").replace("'", "").replace("：", " - ").replace("_", "\_")
			logging.info("输出: " + push.replace("\n", " "))
			photoURL = fCourse["backgroundMedia"]["images"][0]["landscape"]["source"]
			photoURL += "?output-format=jpg&output-quality=80&resize=2880:*"

			logging.getLogger().setLevel(logging.DEBUG)
			bot = telegram.Bot(token = token)
			try:
				bot.send_photo(
					chat_id = chat_id, 
					photo = photoURL,
					caption = '*来自 Today 的通知*\n' + push,
					parse_mode = 'Markdown')
			except:
				logging.error("未能成功发送带有图片的消息")
				bot.send_message(
					chat_id = chat_id,
					text = '*来自 Today 的通知*\n' + push + "\n\n" + photoURL.replace("_", "\_"),
					parse_mode = 'Markdown')
			logging.getLogger().setLevel(logging.INFO)

if appn != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(mark + appn)

logging.info("程序结束")