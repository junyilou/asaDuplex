import asyncio
import json
import logging
from datetime import UTC, datetime
from os.path import basename
from sys import argv
from typing import Optional, Union

from bot import chat_ids
from modules.constants import allRegions, userAgent
from modules.util import disMarkdown, request, session_func, setLogger
from sdk_aliyun import async_post

API = {
	"state": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/stateProvinceList",
	"province": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/storeLocations",
	"image": "https://www.apple.com/careers/images/retail/fy22/hero_hotspot/default@2x.png"
}

TASKS: list[Union["Region", "State"]] = []
RESULTS: list["Store"] = []
FUTURES: dict[str, str] = {}

class Store:

	def __init__(self, **kwargs):
		for k in ["state", "city", "sid", "name"]:
			setattr(self, k, kwargs.get(k, None))
		self.sid: str = kwargs["sid"]
		self.name: str = kwargs["name"]
		self.city: Optional[str] = kwargs.get("city", None)
		self.state: "State" = kwargs["state"]
		self.flag = self.state.flag
		self.stateName = self.state.name
		self.stateCode = self.state.code

	def __repr__(self):
		args = filter(None, [self.flag, self.stateName, self.sid, self.name])
		return f'<Store: {", ".join(args)}>'

	def __hash__(self):
		return hash(("Store", self.sid))

	def __eq__(self, other):
		return (type(self), hash(self)) == (type(other), hash(other))

	def teleInfo(self) -> str:
		city = f"{self.city}, " if self.city is not None else f"{self.stateCode}: "
		return f"*{self.flag} {city}{self.stateName}*\n{self.sid} - {self.name}"

class State:

	def __init__(self, **kwargs):
		self.region: "Region" = kwargs["region"]
		self.fieldID: Optional[str] = kwargs.get("fieldID", None)
		self.code: str = kwargs["code"]
		self.name: str = kwargs["name"]
		self.session = kwargs.get("session", None)
		self.semaphore: Optional[asyncio.Semaphore] = kwargs.get("semaphore", None)
		self.flag = self.region.flag
		self.regionCode = self.region.code

	def __repr__(self):
		args = filter(None, [self.flag, self.code, self.name])
		return f'<State: {", ".join(args)}>'

	def __hash__(self):
		return hash(("State", self.code))

	def __eq__(self, other):
		return (type(self), hash(self)) == (type(other), hash(other))

	async def runner(self) -> None:
		global TASKS, RESULTS

		async with self.semaphore:
			# logging.info(", ".join(["开始下载 province", str(self)]))
			r = await request(session = self.session, ssl = False, headers = userAgent,
				timeout = 3, retryNum = 3, url = API["province"].format(JOBID = self.regionCode),
				params = dict(searchField = "stateProvince", fieldValue = self.fieldID))

		try:
			a = json.loads(r)
		except json.decoder.JSONDecodeError:
			if "Maintenance" in r:
				logging.error("Apple 招贤纳才维护中")
				raise NameError("SERVER")
			else:
				logging.warning(", ".join(["下载失败", "等待重试", str(self)]))
				TASKS.append(self)
		except:
			logging.error(", ".join(["下载失败", "放弃下载", str(self)]))
			TASKS.append(self)

		for c in a:
			RESULTS.append(Store(state = self, city = c["city"], name = c["name"], sid = c["code"]))

class Region:

	def __init__(self, **kwargs):
		self.flag: str = kwargs["flag"]
		self.session = kwargs.get("session", None)
		self.semaphore: Optional[asyncio.Semaphore] = kwargs.get("semaphore", None)
		self.code: str = allRegions[self.flag]["jobCode"]

	def __repr__(self):
		return f'<Region: {", ".join([self.flag, self.code])}>'

	def __hash__(self):
		return hash(("Region", self.flag))

	def __eq__(self, other):
		return (type(self), hash(self)) == (type(other), hash(other))

	async def runner(self) -> None:
		global TASKS

		async with self.semaphore:
			logging.info(", ".join(["开始下载", str(self)]))
			r = await request(session = self.session, ssl = False, headers = userAgent,
				timeout = 3, retryNum = 3, url = API["state"].format(JOBID = self.code))

		try:
			a = json.loads(r)
		except json.decoder.JSONDecodeError:
			if "Maintenance" in r:
				logging.error("Apple 招贤纳才维护中")
				raise NameError("SERVER")
			else:
				logging.warning(", ".join(["下载失败", "等待重试", str(self)]))
				TASKS.append(self)
				return
		except:
			logging.error(", ".join(["下载失败", "放弃下载", str(self)]))
			TASKS.append(self)
			return

		for p in a["searchResults"]:
			TASKS.append(State(
				region = self, fieldID = p["id"], code = p["code"], name = p["stateProvince"],
				session = self.session, semaphore = self.semaphore))

async def entry(session, targets: list[str], check_cancel: bool):

	with open("Retail/savedJobs.json") as r:
		SAVED = eval(r.read())

	STORES: list[Store] = []
	for flag in SAVED:
		if flag == "update":
			continue
		for stateCode in SAVED[flag]:
			if flag not in targets:
				continue
			stateName: str = ""
			for store in SAVED[flag][stateCode]:
				stateName = SAVED[flag][stateCode]["name"]
				if store == "name":
					continue
				STORES.append(Store(
					state = State(region = Region(flag = flag), name = stateName, code = stateCode),
					sid = store, name = SAVED[flag][stateCode][store]))

	global TASKS
	RECORD = {}
	semaphore = asyncio.Semaphore(30)

	TASKS = [Region(flag = i, session = session, semaphore = semaphore) for i in targets if (
		(not i.isalpha()) and (allRegions[i]["jobCode"] is not None))]

	while len(TASKS):
		tasks = TASKS.copy()
		try:
			async with asyncio.TaskGroup() as tg:
				for t in tasks:
					RECORD[id(t)] = RECORD.get(id(t), 0) + 1
					if RECORD[id(t)] > 3:
						logging.error(", ".join(["放弃下载", str(t)]))
						continue
					tg.create_task(t.runner())
			_ = [TASKS.remove(t) for t in tasks]
		except* NameError:
			TASKS = []

	append = False
	pushes = [[], [], []]

	for store in RESULTS:
		if store.flag not in SAVED:
			SAVED[store.flag] = {}
		if store not in STORES:
			append = True
			logging.info(f"记录到新地点 {store.flag} {store.stateName} {store.sid} {store.name}")
			SAVED[store.flag][store.stateCode] = SAVED[store.flag].get(store.stateCode, {"name": store.stateName})
			SAVED[store.flag][store.stateCode][store.sid] = store.name
			linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
			pushes[0].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")
		elif (oldName := SAVED[store.flag][store.stateCode]["name"]) != store.stateName:
			append = True
			logging.info(f"更改名称 {oldName} 为 {store.stateName}")
			SAVED[store.flag][store.stateCode]["name"] = store.stateName
		elif (oldName := SAVED[store.flag][store.stateCode][store.sid]) != store.name:
			append = True
			logging.info(f"更改名称 {oldName} 为 {store.name}")
			SAVED[store.flag][store.stateCode][store.sid] = store.name
			if oldName.startswith("~"):
				linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
				pushes[1].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")

	if check_cancel:
		for store in STORES:
			if store not in RESULTS:
				if store.name.startswith("~"):
					continue
				append = True
				logging.info(f"记录到地点已停止招聘 {store.flag} {store.stateName} {store.sid} {store.name}")
				SAVED[store.flag][store.stateCode][store.sid] = "~" + store.name
				linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
				pushes[2].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")

	for p, t in zip(pushes, ["已开始招聘", "已恢复招聘", "已停止招聘"]):
		if (content := "\n".join(p)):
			push = {
				"mode": "photo-text",
				"text": f"\\#新店新机遇\n{t}\n\n{content}",
				"chat_id": chat_ids[0],
				"parse": "MARK",
				"image": API["image"]
			}
			await async_post(push, session = session)

	if append:
		SAVED["update"] = datetime.now(UTC).strftime("%F %T GMT")
		with open("Retail/savedJobs.json", "w") as w:
			json.dump(SAVED, w, ensure_ascii = False, indent = 2, sort_keys = True)

@session_func
async def main(session, targets: list[str], futures: dict[str, str], check_cancel: bool):
	FUTURE = {
		"filters": {
			"keyword": ["specialist"],
			"postingpostLocation": None,
			"teams": [{"teams.teamID": "teamsAndSubTeams-APPST", "teams.subTeamID": "subTeam-ARSS"}]},
		"page": 1, "locale": "en-us", "sort": "relevance"
	}

	for flag, pipe in futures.items():
		FUTURE["filters"]["postingpostLocation"] = [pipe]
		try:
			r = await request(session = session, url = "https://jobs.apple.com/api/role/search",
				method = "POST", json = FUTURE, mode = "json", ssl = False)
			assert "searchResults" in r
		except:
			logging.warning(f"尝试搜索地区 {flag} 失败")
			continue
		if r["searchResults"]:
			reference = r["searchResults"][0]
			logging.info(f"找到一个新职位信息: {reference['positionId']} {reference['postingTitle']}")
			allRegions[flag] = allRegions.get(flag, {}) | {"jobCode": reference["positionId"]}
			targets.append(flag)

	await entry(session, targets, check_cancel)

setLogger(logging.INFO, basename(__file__))
logging.info("程序启动")

check_cancel = False
if "cancel" in argv:
	argv.remove("cancel")
	check_cancel = True
targets = argv[1:] if len(argv) > 1 else list(allRegions)
asyncio.run(main(targets = targets, futures = FUTURES, check_cancel = check_cancel))

logging.info("程序结束")