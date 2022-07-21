import asyncio
import json
import os
import logging
from sys import argv
from datetime import datetime, timezone

from bot import chat_ids
from sdk_aliyun import async_post
from modules.constants import request, setLogger, RecruitDict, userAgent, disMarkdown, session_func

API = {
	"state": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/stateProvinceList",
	"province": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/storeLocations",
	"image": "https://www.apple.com/careers/images/retail/fy22/hero_hotspot/default@2x.png"
}

TASKS = []
RESULTS = []

async def province(session, semaphore, saved, s, p):
	global RESULTS

	async with semaphore:
		# logging.info(", ".join(["开始下载 province", s, p["code"], p["stateProvince"]]))
		r = await request(
			session = session, ssl = False, headers = userAgent, timeout = 3, retryNum = 3, 
			url = API["province"].format(JOBID = RecruitDict[s]["code"]),
			params = dict(searchField = "stateProvince", fieldValue = p["id"]))

	try:
		a = json.loads(r)
	except json.decoder.JSONDecodeError:
		if "Maintenance" in r:
			logging.error("Apple 招贤纳才维护中")
			return -1
		else:
			logging.warning(", ".join(["下载失败 province", s, p["code"], p["stateProvince"]]))
			return 0
	except:
		logging.warning(", ".join(["下载失败 province", s, p["code"], p["stateProvince"]]))
		return 0

	for c in a:
		n = [s, p["code"], p["stateProvince"], c["city"], c["name"], c["code"]]
		RESULTS.append(n)

	return 1

async def state(session, semaphore, s):
	global TASKS

	async with semaphore:
		logging.info(", ".join(["开始下载 state", s, str(RecruitDict[s]["code"])]))
		r = await request(
			session = session, ssl = False, headers = userAgent, timeout = 3, retryNum = 3, 
			url = API["state"].format(JOBID = RecruitDict[s]["code"]))
		
	try:
		a = json.loads(r)
	except json.decoder.JSONDecodeError:
		if "Maintenance" in r:
			logging.error("Apple 招贤纳才维护中")
			return -1
		else:
			logging.warning(", ".join(["下载失败 state", s, str(RecruitDict[s]["code"])]))
			return 0
	except:
		logging.warning(", ".join(["下载失败 state", s, str(RecruitDict[s]["code"])]))
		return 0

	for p in a["searchResults"]:
		TASKS.append(["province", s, p])

	return 1

def rec(dct, ter):
	for i in dct:
		if type(dct[i]) != str:
			rec(dct[i], ter)
		else:
			ter.append(i)
	return ter

@session_func
async def main(targets, session, limit = None):
	global TASKS
	FAILED = {}

	with open("Retail/savedJobs.json") as r:
		SAVED = eval(r.read())
		saved = rec(SAVED, [])

	for s in targets:
		if (limit != None) and (s not in limit):
			continue
		TASKS.append(["state", s])

	semaphore = asyncio.Semaphore(30)

	while len(TASKS):
		tasks = TASKS.copy()
		coros = []
		for l in tasks:
			if l[0] == "state":
				coros.append(state(session, semaphore, *l[1:]))
			elif l[0] == "province":
				coros.append(province(session, semaphore, saved, *l[1:]))
		results = await asyncio.gather(*coros)

		for t, r in zip(tasks, results):
			if r == 1:
				TASKS.remove(t)
			elif r == -1:
				TASKS = []
			elif r == 0:
				if t[0] == "state":
					taskID = ", ".join(["state", t[1]])
				elif t[0] == "province":
					taskID = ", ".join(["province", t[1], t[2]["code"], t[2]["stateProvince"]])
				FAILED[taskID] = FAILED.get(taskID, 0) + 1
				if FAILED[taskID] > 3:
					logging.error(", ".join(["放弃下载", taskID]))
					TASKS.remove(t)

	append = False

	for flag, pid, pname, city, name, code in RESULTS:

		if code not in saved:
			append = True
			logging.info(f"记录到新地点 {flag} {pname} {code} {name}")

			SAVED[flag][pid] = SAVED[flag].get(pid, {"name": pname})
			SAVED[flag][pid][code] = name

			linkURL = f"https://jobs.apple.com/zh-cn/details/{RecruitDict[flag]['code']}"
			pushAns = f"#新店新机遇\n\n*{flag} {city}, {pname}*\n{code} - {name}\n\n{linkURL}"
				
			push = {
				"mode": "photo-text",
				"text": disMarkdown(pushAns),
				"chat_id": chat_ids[0],
				"parse": "MARK",
				"image": API["image"]
			}

			await async_post(push, session = session)

		elif SAVED[flag][pid]["name"] != pname:
			append = True
			logging.info(f"更改名称 {SAVED[flag][pid]['name']} 为 {pname}")
			SAVED[flag][pid]["name"] = pname
		elif SAVED[flag][pid][code] != name:
			append = True
			logging.info(f"更改名称 {SAVED[flag][pid][code]} 为 {name}")
			SAVED[flag][pid][code] = name

	if append:
		SAVED["update"] = datetime.now(timezone.utc).strftime("%F %T GMT")
		with open("Retail/savedJobs.json", "w") as w:
			w.write(json.dumps(SAVED, ensure_ascii = False, indent = 2))

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")
limit = argv[1:] if len(argv) > 1 else None
asyncio.run(main(targets = RecruitDict, limit = limit))
logging.info("程序结束")