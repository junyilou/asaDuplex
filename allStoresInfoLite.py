import os, time, json, filecmp, difflib, logging, requests
import telegram

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

requests.packages.urllib3.disable_warnings()

asaVersion = "5.11.0"; asaAgent = ".".join(asaVersion.split(".")[:2])
headers = {
	"User-Agent": f"ASA/{asaAgent} (iPhone) ss/3.00",
	"x-ma-pcmh":  f"REL-{asaVersion}",
	"X-MALang":   "zh-CN",
	"X-Apple-I-TimeZone": "GMT+8",
	"X-Apple-I-Locale":   "zh_CN",
	"X-MMe-Client-Info": f"<iPhone13,2> <iPhone OS;14.3;18C66> <com.apple.AuthKit/1 (com.apple.store.Jolly/{asaVersion})>",
	"X-DeviceConfiguration":  f"ss=3.00;dim=1170x2532;m=iPhone;v=iPhone13,2;vv={asaAgent};sv=14.3"}

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, datefmt = '%T')
logging.info("程序启动")

listFile = "Retail/storeList.json"
oldFile  = listFile.replace(".json", "-old.json")

if os.path.isfile(listFile):
	orgListSize = os.path.getsize(listFile)
	os.rename(listFile, oldFile)
else:
	orgListSize = 0

r = requests.get("https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite", headers = headers, verify = False)
with open(listFile, "w") as w:
	dlc = r.text.replace('?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*', '')
	w.write(dlc)

newListSize = os.path.getsize(listFile)
qualify = [filecmp.cmp(listFile, oldFile), newListSize > 0, "Jiefangbei" in dlc]

if qualify == [False, True, True]:
	runtime = time.strftime("%F", time.localtime())

	logging.info("检测到有文件变化，正在生成 changeLog")
	fileLines = []
	fileDiff = f"""
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>allStoresInfoLite</title>
</head>

<body><pre><code>
Apple Store 零售店信息文件
生成于 {runtime}
"""
	for formatFile in [oldFile, listFile]:
		with open(formatFile) as f:
			formatJSON = json.dumps(json.loads(f.read()), ensure_ascii = False, indent = 2)
			fileLines.append(formatJSON.split("\n"))
		if formatFile == listFile:
			with open(listFile.replace(".json", "-format.json"), "w") as w:
				w.write(formatJSON)

	for line in difflib.unified_diff(fileLines[0], fileLines[1]): 
		fileDiff += line + "\n"
	fileDiff += "</code></pre></body></html>"

	with open("/home/storelist.html", "w") as w:
		w.write(fileDiff)
	os.rename(oldFile, listFile.replace(".json", "-" + runtime + ".json"))
	logging.info("文件生成完成")

	bot = telegram.Bot(token = token)
	bot.send_photo(
		chat_id = chat_id, 
		photo = "https://www.apple.com/jp/retail/store/includes/marunouchi/drawer/images/store-drawer-tile-1_medium_2x.jpg",
		caption = '*来自 allStoresInfoLite 的通知*\nApple Store 零售店信息文件已更新 [↗](https://shunitsu.moe/storelist.html)',
		parse_mode = 'MarkdownV2')

elif qualify[0] == True:
	logging.info("没有发现 storeList 文件更新")

elif qualify[1] == False:
	logging.info("下载 allStoresInfoLite 失败")

elif qualify[2] == False:
	logging.error("所下载的 allStoresInfoLite 文件似乎不是英语版本")

try:
	os.rename(oldFile, listFile)
except:
	pass

logging.info("程序结束")