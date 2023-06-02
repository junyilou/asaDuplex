import asyncio
import json
import logging
from datetime import UTC, datetime
from os.path import basename
from random import choice
from sys import argv
from typing import Optional

from bot import chat_ids
from botpost import async_post
from modules.constants import allRegions, userAgent
from modules.util import SemaphoreType, SessionType, disMarkdown, request, session_func, setLogger

API = {
	"state": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/stateProvinceList",
	"province": "https://jobs.apple.com/api/v1/jobDetails/PIPE-{JOBID}/storeLocations",
	"image": "https://www.apple.com/careers/images/retail/fy22/hero_hotspot/default@2x.png"}

class JobObject:
	hashattr: str
	reprattrs: list[str]

	def __eq__(self, other) -> bool:
		if type(self) is not type(other):
			return NotImplemented
		return hash(self) == hash(other)

	def __hash__(self) -> int:
		return hash((self.__class__.__name__, getattr(self, self.hashattr)))

	def __repr__(self) -> str:
		return f'<{self.__class__.__name__}: {", ".join(i for i in (getattr(self, attr) for attr in self.reprattrs) if i)}>'

class TaskObject(JobObject):
	async def runner(self) -> None: ...

TASKS: list[TaskObject] = []
RESULTS: list["Store"] = []
FUTURES: dict[str, str] = {}

class Store(JobObject):
	hashattr = "sid"
	reprattrs = ["flag", "stateName", "sid", "name"]

	def __init__(self, **kwargs) -> None:
		for k in ["state", "city", "sid", "name"]:
			setattr(self, k, kwargs.get(k, None))
		self.sid: str = kwargs["sid"]
		self.name: str = kwargs["name"]
		self.city: Optional[str] = kwargs.get("city", None)
		self.state: "State" = kwargs["state"]
		self.flag: str = self.state.flag
		self.stateName: str = self.state.name
		self.stateCode: str = self.state.code

	def teleInfo(self) -> str:
		city = f"{self.city}, " if self.city is not None else f"{self.stateCode}: "
		return f"*{self.flag} {city}{self.stateName}*\n{self.sid} - {self.name}"

class State(TaskObject):
	hashattr = "code"
	reprattrs = ["flag", "code", "name"]

	def __init__(self, **kwargs) -> None:
		self.region: "Region" = kwargs["region"]
		self.fieldID: Optional[str] = kwargs.get("fieldID", None)
		self.code: str = kwargs["code"]
		self.name: str = kwargs["name"]
		self.session: Optional[SessionType] = kwargs.get("session", None)
		self.semaphore: Optional[SemaphoreType] = kwargs.get("semaphore", None)
		self.flag: str = self.region.flag
		self.regionCode: str = self.region.code

	async def runner(self) -> None:
		global TASKS, RESULTS
		assert isinstance(self.semaphore, SemaphoreType)
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
				return TASKS.append(self)
		except:
			logging.error(", ".join(["下载失败", "放弃下载", str(self)]))
			return TASKS.append(self)
		for c in a:
			RESULTS.append(Store(state = self, city = c["city"], name = c["name"], sid = c["code"]))

class Region(TaskObject):
	hashattr = "flag"
	reprattrs = ["flag", "code"]

	def __init__(self, **kwargs) -> None:
		self.flag: str = kwargs["flag"]
		codes = allRegions[self.flag]["jobCode"]
		assert isinstance(codes, dict)
		self.session: Optional[SessionType] = kwargs.get("session", None)
		self.semaphore: Optional[SemaphoreType] = kwargs.get("semaphore", None)
		self.code: str = str(choice(list(codes.values())))

	async def runner(self) -> None:
		global TASKS
		assert isinstance(self.semaphore, SemaphoreType)
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
				return TASKS.append(self)
		except:
			logging.error(", ".join(["下载失败", "放弃下载", str(self)]))
			return TASKS.append(self)
		for p in a["searchResults"]:
			TASKS.append(State(
				region = self, fieldID = p["id"], code = p["code"], name = p["stateProvince"],
				session = self.session, semaphore = self.semaphore))

async def entry(session: SessionType, targets: list[str], check_cancel: bool) -> None:
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

	TASKS = [Region(flag = i, session = session, semaphore = semaphore) for i in targets if allRegions[i]["jobCode"]]

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
			for t in tasks:
				TASKS.remove(t)
		except* NameError:
			TASKS = []

	append = False
	pushes = {"已开始招聘": [], "已恢复招聘": [], "已停止招聘": []}

	for store in RESULTS:
		if store.flag not in SAVED:
			SAVED[store.flag] = {}
		dct = SAVED[store.flag]
		if store not in STORES:
			append = True
			logging.info(f"记录到新地点 {store.flag} {store.stateName} {store.sid} {store.name}")
			dct[store.stateCode] = dct.get(store.stateCode, {"name": store.stateName})
			dct[store.stateCode][store.sid] = store.name
			linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
			pushes["已开始招聘"].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")
		elif (oldName := dct[store.stateCode]["name"]) != store.stateName:
			append = True
			logging.info(f"更改名称 {oldName} 为 {store.stateName}")
			dct[store.stateCode]["name"] = store.stateName
		elif (oldName := dct[store.stateCode][store.sid]) != store.name:
			append = True
			logging.info(f"更改名称 {oldName} 为 {store.name}")
			dct[store.stateCode][store.sid] = store.name
			if oldName.startswith("~"):
				linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
				pushes["已恢复招聘"].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")

	if check_cancel:
		for store in STORES:
			if store in RESULTS or store.name.startswith("~"):
				continue
			append = True
			logging.info(f"记录到地点已停止招聘 {store.flag} {store.stateName} {store.sid} {store.name}")
			SAVED[store.flag][store.stateCode][store.sid] = "~" + store.name
			linkURL = f"https://jobs.apple.com/zh-cn/details/{store.state.regionCode}"
			pushes["已停止招聘"].append(disMarkdown(store.teleInfo()) + f" [↗]({linkURL})")

	for t, p in pushes.items():
		if not p:
			continue
		push = {
			"mode": "photo-text",
			"text": "\n".join(["\\#新店新机遇", t, "", *p]),
			"chat_id": chat_ids[0],
			"parse": "MARK",
			"image": API["image"]}
		await async_post(push, session = session)

	if append:
		SAVED["update"] = datetime.now(UTC).strftime("%F %T GMT")
		with open("Retail/savedJobs.json", "w") as w:
			json.dump(SAVED, w, ensure_ascii = False, indent = 2, sort_keys = True)

async def future(session: SessionType, futures: dict[str, str]) -> dict[str, dict[str, dict[str, int]]]:
	futures: dict[str, dict[str, dict[str, int]]] = {}
	data = {
		"filters": {
			"postingpostLocation": [],
			"teams":[
				{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSS"},
				{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSCS"},
				{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSLD"}]},
		"page": 1, "locale": "en-us", "sort": "newest"}
	for flag, pipe in futures.items():
		data["filters"]["postingpostLocation"] = [pipe]
		try:
			r = await request(session = session, url = "https://jobs.apple.com/api/role/search",
				method = "POST", json = data, mode = "json", ssl = False)
			assert "searchResults" in r
		except:
			logging.warning(f"尝试搜索地区 {flag} 失败")
			continue
		if not r["searchResults"]:
			continue

		roles = {}
		for i in r["searchResults"]:
			if not i["managedPipelineRole"]:
				continue
			logging.info(f"找到新职位信息: {i['positionId']} {i['postingTitle']}")
			roles[i["transformedPostingTitle"]] = int(i["positionId"])
		if roles:
			futures[flag] = {"jobCode": roles}
	return futures

@session_func
async def main(session: SessionType, targets: list[str], check_cancel: bool) -> None:
	global allRegions
	futures = await future(session, FUTURES)
	if futures:
		allRegions |= futures
		targets.extend(list(futures))
	await entry(session, targets, check_cancel)

setLogger(logging.INFO, basename(__file__))
logging.info("程序启动")

check_cancel = False
if "cancel" in argv:
	argv.remove("cancel")
	check_cancel = True
targets = argv[1:] if len(argv) > 1 else list(allRegions)
asyncio.run(main(targets = targets, check_cancel = check_cancel))

logging.info("程序结束")