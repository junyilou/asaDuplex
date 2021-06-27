import os, time, json, logging
import requests, filecmp, difflib
import telegram

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]
from constants import (
	asaHeaders, setLogger, DIFFhead, DIFFfoot
)

requests.packages.urllib3.disable_warnings()
setLogger(logging.INFO, os.path.basename(__file__))

logging.info("程序启动")

listFile = "Retail/storeList.json"
oldFile  = listFile.replace(".json", "-old.json")

if os.path.isfile(listFile):
	orgListSize = os.path.getsize(listFile)
	os.rename(listFile, oldFile)
else:
	orgListSize = 0

r = requests.get("https://mobileapp.apple.com/mnr/p/cn/retail/allStoresInfoLite", headers = asaHeaders, verify = False)
with open(listFile, "w") as w:
	dlc = r.text.replace('?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*', '')
	w.write(dlc)

newListSize = os.path.getsize(listFile)
qualify = [filecmp.cmp(listFile, oldFile), newListSize > 0]

if qualify == [False, True]:
	runtime = time.strftime("%F", time.localtime())

	logging.info("检测到有文件变化，正在生成 changeLog")
	fileLines = []
	fileDiff = f"""{DIFFhead.replace('DIFF HEAD', 'allStoresInfoLite')}Apple Store 零售店信息文件
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
	fileDiff += DIFFfoot

	with open("/home/centos/www/storelist.html", "w") as w:
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

try:
	os.rename(oldFile, listFile)
except:
	pass

logging.info("程序结束")