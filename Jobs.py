import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from http.cookies import SimpleCookie
from itertools import groupby as _groupby
from random import choice
from typing import Any, Optional, Protocol, Self, Sequence, TypedDict, cast

from bot import chat_ids
from botpost import async_post
from modules.regions import Region, Regions
from modules.util import (AsyncGather, AsyncRetry, RetryExceeded, RetrySignal,
                          SemaphoreType, SessionType, browser_agent,
                          disMarkdown, get_session, session_func,
                          with_semaphore)


class SRC(Protocol):
	def __lt__(self, other, /) -> bool: ...

def groupby[T1: SRC, T2: SRC](iterable: Iterable[T1], key: Callable[[T1], T2]) -> Iterable[tuple[T2, Iterable[T1]]]:
	return _groupby(sorted(iterable, key = key), key = key)

class ServerMaintenance(Exception):
	pass

@dataclass
class APIClass:
	parts: Sequence[str]
	csrf: dict[str, str] = field(default_factory = dict)
	cookies: Optional[SimpleCookie] = None

	def __truediv__(self, other: str) -> Self:
		return type(self)((*self.parts, other), self.csrf, self.cookies)

	def __str__(self) -> str:
		return "/".join(self.parts)

	@AsyncRetry(3, sleep = 1)
	async def request(self,
		session: Optional[SessionType] = None,
		method: str = "GET", mode: str = "json", log_name: str = "",
		extra_headers: dict[str, str] = {}, **kwargs) -> Any:
		default_headers = browser_agent | self.csrf
		kwargs |= {"headers": default_headers | extra_headers,
			"allow_redirects": False, "ssl": False, "cookies": self.cookies}
		async with get_session(session) as ses:
			try:
				async with ses.request(method, "/".join(self.parts), **kwargs) as response:
					if response.status > 300 and response.status < 400:
						raise ServerMaintenance()
					elif response.status >= 400:
						response.raise_for_status()
					elif mode == "cookies":
						return response.headers, response.cookies
					elif mode == "text":
						return await response.text()
					elif mode == "json":
						return await response.json()
			except ServerMaintenance:
				raise
			except Exception as exp:
				logger.log(17, f"[等待重试] {log_name or "请求任务"}: {exp.__class__.__name__}({exp})")
				raise RetrySignal(exp)

	async def get_csrf(self, session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> None:
		try:
			async with with_semaphore(semaphore):
				logger.log(17, "[开始] CSRF")
				headers, cookies = await (self / "csrfToken").request(session, mode = "cookies", log_name = "CSRF")
		except ServerMaintenance:
			raise
		except RetryExceeded as exp:
			logger.error(f"[请求失败] CSRF: {exp.message}")
			return

		self.csrf = {"X-Apple-CSRF-Token": headers["X-Apple-CSRF-Token"]}
		self.cookies = cookies

API = APIClass("https://jobs.apple.com/api".split("/"))
logger = logging.getLogger()

class StateDict(TypedDict):
	name: str
	stores: dict[str, str]

class RegionDict(TypedDict):
	locations: dict[str, StateDict]
	positions: dict[str, dict[str, str]]

@dataclass
class Locale:
	region: Region
	positions: dict[str, dict[str, str]] = field(repr = False, default_factory = dict)

	def get_position(self) -> "Position":
		return Position(*choice(list(self.positions["managed"].items())), self.region)

	async def get_positions_base(self, page: int = 1,
		session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> tuple[list["RichPosition"], int]:
		data = {"filters": {
			"postingpostLocation": [f"postLocation-{self.region.post_location}"],
			"teams":[{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSS"},
				{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSCS"},
				{"teams.teamID":"teamsAndSubTeams-APPST","teams.subTeamID":"subTeam-ARSLD"}]},
			"page": page, "locale": self.region.locale.replace("_", "-").lower(), "sort": "newest", "query": ""}
		await API.get_csrf(session, semaphore)
		log_name = f"获取职位 {self} (第 {page} 页)"
		try:
			logger.log(20, f"[开始] {log_name}")
			async with with_semaphore(semaphore):
				r = await (API / "role" / "search").request(session,
					method = "POST", log_name = log_name, json = data)
			logger.log(17, f"[完成] {log_name}")
		except ServerMaintenance:
			raise
		except RetryExceeded as exp:
			logger.error(f"[请求失败] {log_name}: {exp.message}")
			return [], 0

		g = [RichPosition(id = i["positionId"],
			slug = i["transformedPostingTitle"],
			region = self.region,
			update = datetime.fromisoformat(i["postDateInGMT"]).strftime("%F"),
			title = i["postingTitle"].strip(),
			location = next((l["name"] for l in i["locations"]), "").strip(),
			managed = i["managedPipelineRole"]) for i in r["searchResults"]]
		return g, r["totalRecords"]

	async def get_positions(self,
		max_page: int = 3,
		managed: Optional[bool] = None,
		later_than: str = "",
		session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list["RichPosition"]:
		results, total, page = [], 1, 1
		while len(results) < total and page <= max_page:
			positions, total = await self.get_positions_base(page, session, semaphore)
			results.extend(positions)
			page += 1
		l = (i for i in results if managed is not False or i.update >= later_than)
		return [i for i in l if managed is None or i.managed == managed]

	async def get_stores(self, session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list["Store"]:
		states = await self.get_position().get_states(session, semaphore)
		stores = await AsyncGather(state.get_stores(session, semaphore) for state in states)
		return [i for j in stores for i in j]

@dataclass(order = True)
class Position:
	id: str
	slug: str = field(repr = False)
	region: Region

	async def get_states(self, session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list["State"]:
		api = API / "v1" / "jobDetails" / f"PIPE-{self.id}" / "stateProvinceList"
		log_name = f"获取 {self}"
		try:
			async with with_semaphore(semaphore):
				logger.log(20, f"[开始] {log_name}")
				r = await api.request(session, log_name = log_name)
				logger.log(17, f"[完成] {log_name}")
		except ServerMaintenance:
			raise
		except RetryExceeded as exp:
			logger.error(f"[请求失败] {log_name}: {exp.message}")
			return []
		return [State(code = p["code"], name = p["stateProvince"],
			field_val = p["id"], position = self) for p in r["searchResults"]]

	@property
	def url(self) -> str:
		locale = self.region.locale.replace("_", "-").lower()
		return f"https://jobs.apple.com/{locale}/details/{self.id}/{self.slug}"

@dataclass
class RichPosition(Position):
	update: str
	title: str
	location: str
	managed: bool

	@property
	def telename(self) -> str:
		return f"*{self.location}*\n{self.id} - {self.title}"

@dataclass
class State:
	code: str
	name: str
	position: Position = field(repr = False)
	field_val: str = field(repr = False, default = "")

	def __post_init__(self) -> None:
		self.args: tuple[str, str] = self.code, self.name

	async def get_stores(self, session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list["Store"]:
		assert self.position
		api = API / "v1" / "jobDetails" / f"PIPE-{self.position.id}" / "storeLocations"
		log_name = f"获取招聘地点 {self}"
		try:
			async with with_semaphore(semaphore):
				logger.log(19, f"[开始] {log_name}")
				r = await api.request(session, log_name = log_name, params = {
					"searchField": "stateProvince", "fieldValue": self.field_val})
				logger.log(17, f"[完成] {log_name}")
		except ServerMaintenance:
			raise
		except RetryExceeded as exp:
			logger.error(f"[请求失败] {log_name}: {exp.message}")
			return []
		stores = [Store(code = c["code"], name = c["name"], state = self, city = c["city"]) for c in r]
		for store in stores:
			logger.log(18, f"[门店] {store}")
		return stores

@dataclass(order = True)
class Store:
	code: str
	name: str
	state: State = field(repr = False)
	city: str = ""

	@property
	def telename(self) -> str:
		flag = self.state.position.region.flag
		city = f"{self.city}, " if self.city else ""
		return f"*{flag} {city}{self.state.name}*\n{self.code} - {self.name}"

def load_file() -> dict[str, RegionDict]:
	with open("Retail/savedJobs.json") as r:
		j = json.load(r)
		j.pop("update")
		p = cast(dict[str, RegionDict], j)
	return p

def set_logger(args: Namespace) -> None:
	from os.path import basename
	global logger
	level, datefmt = logging.INFO - args.verbose, "%F %T"
	format = "[%(asctime)s %(levelname)s] %(message)s"
	file_args: dict[str, Any] = {"filename": f"logs/{basename(__file__)}.log", "filemode": "a"} if not args.debug else {}
	logging.basicConfig(format = format, level = level, datefmt = datefmt, **file_args)
	_ = [logging.addLevelName(i, "INFO") for i in range(17, 20)]
	logger = logging.getLogger("Jobs")

async def entry(flags: list[str], session: SessionType) -> None:
	p = load_file()
	saved = {code: Store(code, name, State(state_code, state["name"], Position("", "", Regions[flag])))
		for flag, region in p.items() for state_code, state in region["locations"].items()
		for code, name in state["stores"].items()}
	flags = flags or list(Regions)

	cancel = False
	results: list[Store] = []
	semaphore = asyncio.Semaphore(10)
	locales = (Locale(Regions[flag], p[flag]["positions"]) for flag in flags if flag in Regions and not flag.isascii())
	tasks = [asyncio.create_task(locale.get_stores(session, semaphore)) for locale in locales]
	for coro in asyncio.as_completed(tasks):
		try:
			results.extend(await coro)
		except ServerMaintenance:
			logger.error("服务器维护中")
			cancel = True
			break
	if cancel:
		_ = [t.cancel() for t in tasks]

	updated = None
	arrival: list[Store] = []
	for i in results:
		if i.code in saved:
			if (n := i.name) != (o := saved[i.code].name):
				updated = True
				logging.info(f"[更新名称] {i.code}: {o} -> {n}")
				saved[i.code] = i
		else:
			updated = True
			logging.info(f"[找到新店] {i.code}: {i.name}")
			arrival.append(i)
			saved[i.code] = i

	if not updated:
		logging.info("没有找到更新")
		return

	if arrival and not args.local:
		logger.info(f"[推送通知] {len(arrival)} 家新零售店")
		title = ["\\#新店新机遇", "已开始招聘", ""]
		body = [f"{disMarkdown(s.telename)} [↗]({s.state.position.url})" for s in arrival]
		image = "https://www.apple.com/careers/images/retail/fy22/hero_hotspot/default@2x.png"
		push = {"mode": "photo-text", "text": "\n".join(title + body),
			"chat_id": chat_ids[0], "parse": "MARK", "image": image}
		await async_post(push)

	logging.info(f"[更新文件] {len(saved)} 家零售店")
	write: dict[str, Any] = {flag: {"locations": {state_code:
		{"name": state_name, "stores": {store.code: store.name for store in stores}}
		for (state_code, state_name), stores in groupby(state_stores, lambda i: i.state.args)}}
		for flag, state_stores in groupby(saved.values(), lambda i: i.state.position.region.flag)}
	for flag, region in p.items():
		write[flag]["positions"] = region["positions"]
	write["update"] = f"{datetime.now():%F %T}"
	with open("Retail/savedJobs.json", "w") as w:
		json.dump(write, w, indent = 2, ensure_ascii = False, sort_keys = True)

async def position(flags: list[str], managed: bool, session: SessionType) -> None:
	p = load_file()
	flags = flags or list(Regions)
	updated: tuple[int, int] = (0, 0)
	added: list[RichPosition] = []
	stopped: int = 0

	for flag in flags:
		if flag not in Regions or flag.isascii():
			continue
		added.clear()
		stopped = 0
		key = "managed" if managed else "standalone"
		local = p[flag]["positions"][key]
		later_than = f"{datetime.now().year}-01-01"
		locale = Locale(Regions[flag])
		try:
			r = await locale.get_positions(managed = managed,
				later_than = later_than, session = session)
		except ServerMaintenance:
			logger.error("服务器维护中")
			break
		remote = {p.id: p for p in r}
		for pos in (v for i, v in remote.items() if i not in local):
			added.append(pos)
			logger.info(f"[新增招聘] {pos.id}: {pos.title}, {pos.location}, {pos.update}")
		if managed:
			for pid, slug in ((i, v) for i, v in local.items() if i not in remote):
				stopped += 1
				logger.info(f"[停止招聘] {pid}: {slug}")
		p[flag]["positions"][key] = {k: v.slug for k, v in remote.items()}

		if added and not managed and not args.local:
			logger.info(f"[推送通知] {len(added)} 个新职位")
			title = ["\\#新店新机遇", "新增独立职位", ""]
			body = [f"{flag} {disMarkdown(s.telename)} [↗]({s.url})" for s in added]
			image = "https://www.apple.com/careers/images/retail/fy22/hero-welcome_poster/desktop@2x.png"
			push = {"mode": "photo-text", "text": "\n".join(title + body),
				"chat_id": chat_ids[0], "parse": "MARK", "image": image}
			await async_post(push)

		updated = (updated[0] + len(added), updated[1] + stopped)

	if any(updated):
		logging.info(f"[更新文件] 新增职位: {updated[0]} 个, 停止职位: {updated[1]} 个")
		write: dict[str, Any] = p
		write["update"] = f"{datetime.now():%F %T}"
		with open("Retail/savedJobs.json", "w") as w:
			json.dump(write, w, indent = 2, ensure_ascii = False, sort_keys = True)
	else:
		logging.info("没有找到更新")

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	set_logger(args)
	logger.info("程序启动")
	if args.position:
		await position(args.flags, True, session)
	elif args.standalone:
		await position(args.flags, False, session)
	else:
		await entry(args.flags, session)
	logger.info("程序结束")

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("flags", metavar = "FLAG", type = str, nargs = "*", help = "指定国家或地区旗帜")
	parser.add_argument("-d", "--debug", action = "store_true", help = "打印调试信息")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	parser.add_argument("-p", "--position", action = "store_true", help = "寻找普通职位模式")
	parser.add_argument("-s", "--standalone", action = "store_true", help = "寻找独立职位模式")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "记录调试信息")
	args = parser.parse_args()
	asyncio.run(main(args))