import os
import json
import logging
import filecmp
import difflib
import asyncio
from datetime import datetime

from modules.constants import asaHeaders, setLogger, request, DIFFhead, DIFFfoot
from sdk_aliyun import async_post
from bot import chat_ids

async def main():
	listFile = "Retail/storeList.json"
	oldFile  = listFile.replace(".json", "-old.json")

	if os.path.isfile(listFile):
		orgListSize = os.path.getsize(listFile)
		os.rename(listFile, oldFile)
	else:
		orgListSize = 0

	url = "https://mobileapp.apple.com/retailapp/p/cn/retail/allStoresInfoLite"
	repl = "?interpolation=progressive-bicubic&output-quality=85&output-format=jpg&resize=312:*"
	
	r = await request(session = None, url = url, headers = asaHeaders, ssl = False)
	with open(listFile, "w") as w:
		dlc = r.replace(repl, "")
		w.write(dlc)

	newListSize = os.path.getsize(listFile)
	qualify = [filecmp.cmp(listFile, oldFile), newListSize > 0]

	if qualify == [False, True]:
		runtime = datetime.now().strftime("%F")

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

		with open("/root/html/storelist.html", "w") as w:
			w.write(fileDiff)
		os.rename(oldFile, listFile.replace(".json", "-" + runtime + ".json"))
		logging.info("文件生成完成")

		push = {
			"mode": "photo-text",
			"text": "*来自 allStoresInfoLite 的通知*\nApple Store 零售店信息文件已更新 [↗](http://aliy.un/html/storelist.html)",
			"parse": "MARK",
			"image": "https://www.apple.com/jp/retail/store/includes/marunouchi/drawer/images/store-drawer-tile-1_medium_2x.jpg",
			"chat_id": chat_ids[0]
		}
		
		await async_post(push)

	elif qualify[0] == True:
		logging.info("没有发现 storeList 文件更新")
	elif qualify[1] == False:
		logging.info("下载 allStoresInfoLite 失败")

	try:
		os.rename(oldFile, listFile)
	except:
		pass

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")
asyncio.run(main())
logging.info("程序结束")