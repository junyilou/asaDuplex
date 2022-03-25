import os
import json
import logging
import asyncio
import aiohttp
from datetime import datetime

from sdk_aliyun import async_post
from modules.constants import request as request
from modules.constants import RecruitDict, disMarkdown, setLogger, userAgent
from bot import chat_ids

stdout = lambda p: print(datetime.now().strftime("[%F %T] ") + p)
from sys import argv
if len(argv) > 1:
	if "special" in argv:
		RecruitDict = {"🇨🇳": {"name": "中国", "code": 114438030}}
	if "logging" in argv:
		stdout = logging.info

wAns = ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop@2x.jpg"
with open("Retail/savedJobs.txt") as m:
	mark = m.read()

async def entry(session, region):
	global wAns
	name = RecruitDict[region]["name"]
	code = RecruitDict[region]["code"]

	try:
		stdout(f"下载{name}文件")
		state = await request(
			session = session, 
			url = f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{code}/stateProvinceList", 
			ident = None, ssl = False)
		states = json.loads(state)["searchResults"]
	except aiohttp.ClientError as exp:
		logging.error(f"下载{name}文件错误 {exp}")
		return
	except json.decoder.JSONDecodeError:
		if "Maintenance" in state:
			logging.error("Apple 招贤纳才维护中")
			return
		else:
			logging.error(f"打开{name}文件错误")
			return
	
	stdout(f"下载{name} {len(states)} 个行政区")
	tasks = [request(
		session = session, 
		url = f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{code}/storeLocations?searchField=stateProvince&fieldValue={city['id']}", 
		ident = f"{name} - {city['id']}",
		ssl = False) for city in states]
	cities = await asyncio.gather(*tasks)

	for ident in cities:
		if isinstance(ident[0], Exception):
			try:
				raise ident[0]
			except aiohttp.ClientError:
				logging.error(f"下载{ident[1]} 文件错误")
				continue
		
		try:
			city = json.loads(ident[0])
		except json.decoder.JSONDecodeError:
			logging.error(f"打开{ident[1]} 文件错误")
			continue

		for store in city:
			rollout = store["code"]
			cityID = ident[1].split(" - ")[1]
			if not rollout in mark:
				stdout(f"找到{name}新编号 {rollout}")
				
				wAns += f"{region}{rollout}, "
				linkURL = f"https://jobs.apple.com/zh-cn/details/{code}"
				pushAns = f"#新店新机遇\n\n*{region} {name}新增招聘地点*\n{rollout} - {store['name']}\n\n{linkURL}"
				
				push = {
					"mode": "photo-text",
					"text": disMarkdown(pushAns),
					"chat_id": chat_ids[0],
					"parse": "MARK",
					"image": imageURL
				}
				await async_post(push, session = session, logger = stdout)

async def main():
	async with aiohttp.ClientSession(headers = userAgent) as session:
		tasks = [entry(session, state) for state in RecruitDict]
		await asyncio.gather(*tasks)
	if wAns != "":
		stdout("正在更新 savedJobs 文件")
		with open("Retail/savedJobs.txt", "w") as m:
			m.write(mark + wAns)

setLogger(logging.INFO, os.path.basename(__file__))
stdout("程序启动")
asyncio.run(main())
stdout("程序结束")