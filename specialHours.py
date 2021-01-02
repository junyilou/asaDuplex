import json, datetime, os, logging, time, requests
from storeInfo import *
import telegram

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
requests.packages.urllib3.disable_warnings()

master = StoreNation("🇨🇳") + StoreNation("🇭🇰") + StoreNation("🇲🇴") + StoreNation("🇹🇼")

asaVersion = "5.9.0"; remoteAsaVersion = 0
rpath = os.path.expanduser('~') + "/Retail/"
formatAsaVersion = int("".join(asaVersion.split(".")))

with open(rpath + "storeInfo.json") as w:
	storeInfo = json.loads(w.read())["name"]

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
runtime = datetime.datetime.now().strftime("%F")

weekList = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
headers = {
	"User-Agent": "ASA/" + asaVersion + " (iPhone) ss/2.00",
	"x-ma-pcmh":  "REL-" + asaVersion,
	"X-MALang":   "zh-CN",
	"X-DeviceConfiguration":  "ss=2.00;dim=828x1792;m=iPhone;v=iPhone12,1;vv=" + asaVersion + ";sv=14.0.1"}

def fileWrite(fileloc, writer): 
	with open(fileloc, "w") as fout:
		fout.write(writer)

def fileOpen(fileloc):
	try: 
		with open(fileloc) as fin:
			return fin.read()
	except FileNotFoundError:
		logging.error(fileloc + " 文件不存在")
		return None

logging.info("正在确认远程 Apple Store app 版本...")
try: lookup = requests.get("https://itunes.apple.com/cn/lookup?id=375380948").json()
except: pass
else: 
	remoteAsaVersion = int("".join(lookup["results"][0]["version"].split(".")))
if remoteAsaVersion in range(10, 101): 
	remoteAsaVersion *= 10
if remoteAsaVersion > formatAsaVersion:
	asaVersion = ".".join(list(str(remoteAsaVersion)))
	logging.info("从远程获得了新的 Apple Store app 版本 " + asaVersion)

allSpecial = {"created": runtime}; comparison = ""
try: orgjson = json.loads(fileOpen(rpath + "storeHours.json"))
except: orgjson = {}

for sid, sn in master:
	logging.info("正在下载 Apple " + sn + " 的细节文件...")

	url = "https://mobileapp.apple.com/mnr/p/cn/retail/storeDetails?storeNumber=R" + sid

	storeDiff = ""
	storedict = requests.get(url, verify = False, headers = headers).json()["allStoreHoursMergedResponse"]

	if not storedict["hasSpecialHours"]: continue
	regular = storedict["regularHours"]
	special = storedict["specialHours"]

	regularHours = [""] * 7
	for r in regular:
		rRange = r["range"].replace(":", "")
		if len(rRange) == 2:
			regularHours[weekList.index(rRange)] = r["time"]
		elif " – " in rRange:
			(rangeA, rangeB) = rRange.split(" – ")
			for i in range(weekList.index(rangeA), weekList.index(rangeB) + 1):
				regularHours[i] = r["time"]
		elif rRange == "暂时关闭":
			regularHours = ["已关闭"] * 7
		else:
			regularHours = ["N/A"] * 7
			logging.error("Apple " + sn + " 的一般营业时间未被正确匹配到")

	appendJSON = {}
	for s in special:
		sWeekday = datetime.datetime.strptime(s["specialDate"], '%Y年%m月%d日').weekday()
		fRegular = regularHours[sWeekday]
		
		if s["isClosed"] == "Y": 
			fSpecial = "已关闭"
		else: 
			fSpecial = s["startTime"] + " – " + s["endTime"]

		try:
			comments = s["comments"]
		except KeyError:
			fComment = "[" + s["reason"] + "]"
		else:
			if comments != "": fComment = "[" + s["reason"] + "] " + comments
			else: fComment = "[" + s["reason"] + "]"

		appendJSON[s["specialDate"]] = {"regular": fRegular, "special": fSpecial, "comment": fComment}

		try: 
			orgSpecial = orgjson[sid][s["specialDate"]]["special"]
		except KeyError:
			storeDiff += " " * 8 + s["specialDate"] + "：新增 " + fSpecial + "\n"
			logging.info("Apple " + sn + " " + s["specialDate"] + " 新增 " + fSpecial)
		else: 
			if orgSpecial != fSpecial:
				storeDiff += " " * 8 + s["specialDate"] + "：由 " + orgSpecial + " 改为 " + fSpecial + "\n"
				logging.info("Apple " + sn + " " + s["specialDate"] + " 改为 " + fSpecial)
	
	try: 
		oload = orgjson[sid]
	except KeyError: 
		pass
	else:
		for odate in oload.keys():
			if odate == "storename": 
				continue
			odatetime = datetime.datetime.strptime(odate, '%Y年%m月%d日')
			if odatetime < datetime.datetime.now(): 
				continue
			try:
				newSpecial = appendJSON[odate]
			except KeyError:
				storeDiff += " " * 8 + odate + "：取消 " + oload[odate]["special"] + "\n"
				logging.info("Apple " + sn + " " + odate + " 取消 " + oload[odate]["special"])

	if len(appendJSON):
		allSpecial[sid] = {"storename": sn, **appendJSON}
	if len(storeDiff):
		comparison += "    Apple " + sn + "\n" + storeDiff

jOut = json.dumps(allSpecial, ensure_ascii = False, indent = 2)
os.system("mv " + rpath + "storeHours.json " + rpath + "storeHours-" + runtime + ".json")
logging.info("写入新的 storeHours.json")
fileWrite(rpath + "storeHours.json", jOut)

if len(comparison):
	tOut = "Apple Store 特别营业时间\n生成于 " + runtime + "\n\n变化：\n" + comparison + "\n原始 JSON:\n" + jOut
	fileDiff = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>specialHours</title>
</head>

<body><pre><code>
"""
	fileDiff += tOut + "</code></pre></body></html>"
	fileWrite("/home/storeHours.html", fileDiff)
	logging.info("文件生成完成")

	logging.getLogger().setLevel(logging.DEBUG)
	bot = telegram.Bot(token = token)
	bot.send_photo(
		chat_id = chat_id, 
		photo = "https://www.apple.com/retail/store/flagship-store/drawer/michiganavenue/images/store-drawer-tile-1_medium_2x.jpg",
		caption = ('*来自 specialHours 的通知*\n' + str(comparison.count("Apple")) + ' 个 Apple Store 有特别营业时间变化\n\nhttps://shunitsu.moe/storeHours.html'),
		parse_mode = 'Markdown')
	logging.getLogger().setLevel(logging.INFO)

else: 
	os.remove(rpath + "storeHours-" + runtime + ".json")
	logging.info("没有发现 storeHours 文件更新")

logging.info("程序结束")