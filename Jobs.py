import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from http.cookies import SimpleCookie
from random import choice
from typing import Any, Optional, Self, TypedDict
from urllib.parse import unquote
from uuid import uuid4

from tenacity import (AsyncRetrying, RetryCallState,
                      retry_if_not_exception_type, stop_after_attempt,
                      wait_fixed)

from bot import async_post, chat_ids
from modules.regions import Region, Regions
from modules.util import (AsyncGather, SessionType, browser_agent, disMarkdown,
                          get_session, session_func)

RETAIL_FILTER  = {"teams":[{"team":"teamsAndSubTeams-APPST","subTeam":"subTeam-ARSS"},
	{"team":"teamsAndSubTeams-APPST","subTeam":"subTeam-ARSCS"},
	{"team":"teamsAndSubTeams-APPST","subTeam":"subTeam-ARSLD"}]}

class ServerMaintenance(Exception):
	pass

class ResponseError(Exception):
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

	async def request(self,
		session: Optional[SessionType] = None,
		method: str = "GET", mode: str = "json", log_name: str = "",
		extra_headers: dict[str, str] = {}, **kwargs) -> Any:

		async def _request_impl() -> Any:
			nonlocal kwargs
			default_headers = browser_agent | self.csrf
			kwargs |= {"headers": default_headers | extra_headers, "timeout": 10,
				"allow_redirects": False, "ssl": False, "cookies": self.cookies}
			kwargs["headers"]["x-b3-traceid"] = str(uuid4())
			async with get_session(session) as ses:
				async with ses.request(method, "/".join(self.parts), **kwargs) as response:
					if response.status > 300 and response.status < 400:
						raise ServerMaintenance()
					elif mode == "cookies":
						return response.headers, response.cookies
					elif mode == "json":
						j = await response.json()
						if "res" in j:
							return j["res"]
						elif "error" in j:
							raise ResponseError(j["error"])
						response.raise_for_status()
						raise ResponseError()

		def log_retry(retry_state: RetryCallState) -> None:
			if retry_state.outcome and retry_state.outcome.failed:
				exp = retry_state.outcome.exception()
				logger.log(17, f"[等待重试] {log_name or "请求任务"}: {exp.__class__.__name__}({exp!r})")

		retryer = AsyncRetrying(
			stop = stop_after_attempt(3), wait = wait_fixed(1), reraise = True, after = log_retry,
			retry = retry_if_not_exception_type((ResponseError, ServerMaintenance)))
		return await retryer(_request_impl)

	async def get_csrf(self, session: Optional[SessionType] = None) -> None:
		try:
			logger.log(17, "[开始] CSRF")
			headers, cookies = await (self / "CSRFToken").request(session, mode = "cookies", log_name = "CSRF")
		except ServerMaintenance:
			raise
		except Exception as exp:
			logger.error(f"[请求失败] CSRF: {exp!r}")
			return

		self.csrf = {"X-Apple-CSRF-Token": headers["X-Apple-CSRF-Token"]}
		self.cookies = cookies

API = APIClass("https://jobs.apple.com/api/v1".split("/"))
logger = logging.getLogger()

class StateDict(TypedDict):
	name: str
	stores: dict[str, str]

class RegionDict(TypedDict):
	locations: dict[str, StateDict]
	positions: dict[str, str]

class FileDict(TypedDict):
	update: str
	regions: dict[str, RegionDict]

@dataclass(order = True)
class Position:
	id: str
	slug: str = field(repr = False)
	region: Region

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

@dataclass(order = True)
class Store:
	code: str
	name: str
	state: "State" = field(repr = False)
	city: str = field(default = "")

	@property
	def telename(self) -> str:
		flag = self.state.region.flag
		city = f"{self.city}, " if self.city else ""
		return f"*{flag} {city}{self.state.name}*\n{self.code} - {self.name}"

@dataclass
class State:
	code: str
	name: str
	region: Region
	stores: dict[str, Store] = field(default_factory = dict, repr = False)

	async def get_stores(self, position: Position,
		session: Optional[SessionType] = None) -> dict[str, Store]:
		api = API / "storeLocations"
		log_name = f"获取招聘地点 {self}"
		try:
			logger.log(19, f"[开始] {log_name}")
			r = await api.request(session, log_name = log_name, params = {
				"jobId": f"PIPE-{position.id}", "fieldValue": f"postLocation-{self.code}"})
			logger.log(17, f"[完成] {log_name}")
		except ServerMaintenance:
			raise
		except ResponseError as exp:
			logger.log(17, f"[请求错误] {log_name}: {exp!r}")
			return self.stores
		except Exception as exp:
			logger.error(f"[请求失败] {log_name}: {exp!r}")
			return self.stores
		remote = {}
		for c in r:
			code = c["locationId"].removeprefix("postLocation-")
			remote[code] = Store(code = code, name = c["name"], state = self, city = c["city"] or "")
		for store in remote.values():
			logger.log(18, f"[门店] {store}")
		return remote

	def dumps(self) -> StateDict:
		return {"name": self.name, "stores": {s.code: s.name for s in self.stores.values()}}

@dataclass
class Locale:
	region: Region
	data: RegionDict = field(repr = False)
	updated: bool = False
	states_to_run: list[str] = field(default_factory = list, repr = False)
	new_stores: list[Store] = field(default_factory = list, repr = False)
	states: list[State] = field(init = False, repr = False)
	positions: Sequence[Position] = field(init = False, repr = False)
	position: Optional[Position] = field(init = False, repr = False)

	def __post_init__(self) -> None:
		states: list[State] = []
		for code, state in self.data["locations"].items():
			inst = State(code, state["name"], self.region)
			inst.stores = {code: Store(code, name, inst) for code, name in state["stores"].items()}
			states.append(inst)
		self.states = states
		self.states_to_run = [state.code for state in states]
		self.positions = [Position(id, slug, self.region) for id, slug in self.data["positions"].items()]

	async def choose_position(self, session: Optional[SessionType] = None) -> Optional[Position]:
		if not self.positions:
			self.positions = await self.fetch_positions(managed = True,
				filters = RETAIL_FILTER, session = session)
		self.position = choice(self.positions) if self.positions else None

	async def fetch_positions(self,
		max_page: int = 3,
		managed: Optional[bool] = None,
		later_than: str = "",
		filters: dict[str, Any] = RETAIL_FILTER,
		session: Optional[SessionType] = None) -> list[RichPosition]:

		async def get_positions_base(page: int = 1) -> tuple[list[RichPosition], int]:
			data = {"filters": {"locations": [f"postLocation-{self.region.post_location}"]} | filters,
				"page": page, "locale": self.region.locale.replace("_", "-"), "sort": "newest",
				"query": "", "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}}
			await API.get_csrf(session)
			log_name = f"获取职位 {self} (第 {page} 页)"
			try:
				logger.log(19, f"[开始] {log_name}")
				r = await (API / "search").request(session,
					method = "POST", log_name = log_name, json = data)
				logger.log(17, f"[完成] {log_name}")
			except ServerMaintenance:
				raise
			except Exception as exp:
				logger.error(f"[请求失败] {log_name}: {exp!r}")
				return [], 0

			g = [RichPosition(id = i["positionId"],
				slug = unquote(i["transformedPostingTitle"]),
				region = self.region,
				update = datetime.fromisoformat(i["postDateInGMT"]).strftime("%F"),
				title = i["postingTitle"].strip(),
				location = next((l["name"] for l in i["locations"]), "").strip(),
				managed = i["managedPipelineRole"]) for i in r["searchResults"]]
			return g, r["totalRecords"] or 0

		results: list[RichPosition] = []
		total = page = 1
		while len(results) < total and (not max_page or page <= max_page):
			positions, total = await get_positions_base(page)
			results.extend(positions)
			page += 1
		l = (i for i in results if managed is not False or i.update >= later_than)
		return sorted((i for i in l if managed is None or i.managed == managed),
			key = lambda r: (r.update, r.id))

	async def main(self, session: Optional[SessionType] = None) -> list[Store]:
		async def entry(position: Position, state: State) -> list[Store]:
			new_stores: list[Store] = []
			remote = await state.get_stores(position, session)
			for code, store in remote.items():
				if code not in state.stores:
					self.updated = True
					logger.info(f"[找到新店] {code}: {store.name}")
					new_stores.append(store)
				elif (store.name != state.stores[code].name):
					self.updated = True
					logger.info(f"[更新名称] {code}: {state.stores[code].name} -> {store.name}")
			if removal := [i for i in state.stores if i not in remote]:
				logger.log(18, f"[不存在门店] {", ".join(remote[r].code for r in removal)}")
			state.stores = remote
			return new_stores

		if not self.states or not self.states_to_run:
			return []
		await self.choose_position(session)
		if not self.position:
			return []
		log_name = f"获取 {self.position}"
		logger.log(19, f"[开始] {log_name}")
		results = await AsyncGather((entry(self.position, state) for state in self.states
			if state.code in self.states_to_run), limit = 10, return_exceptions = True)
		self.new_stores = [store for i in results if not isinstance(i, Exception) for store in i]
		logger.log(17, f"[完成] {log_name}")
		return self.new_stores

	def dumps(self) -> RegionDict:
		return {"locations": {state.code: state.dumps() for state in self.states},
			"positions": {p.id: p.slug for p in self.positions}}

def load_db() -> FileDict:
	with open("Retail/savedJobs.json") as r:
		db = json.load(r)
	return db

def save_db(db: FileDict, locales: list[Locale]) -> None:
	if not any(locale.updated for locale in locales):
		return
	logging.info(f"[更新文件] {len(locales)} 个地区")
	db["update"] = datetime.now().strftime("%F %T")
	db["regions"].update({locale.region.flag: locale.dumps() for locale in locales if locale.updated})
	with open("Retail/savedJobs.json", "w") as w:
		json.dump(db, w, indent = 2, ensure_ascii = False, sort_keys = True)

def set_logger(verbosity: int, debug: bool) -> None:
	from os.path import basename
	global logger
	level, datefmt = logging.INFO - verbosity, "%F %T"
	format = "[%(asctime)s %(levelname)s] %(message)s"
	file_args: dict[str, Any] = {"filename": f"logs/{basename(__file__)}.log", "filemode": "a"} if not debug else {}
	logging.basicConfig(format = format, level = level, datefmt = datefmt, **file_args)
	for i in range(17, 20):
		logging.addLevelName(i, "INFO")
	logger = logging.getLogger("Jobs")

async def entry(flags: list[str], states: list[str], session: SessionType) -> None:
	db = load_db()
	locales = [Locale(Regions[i], db["regions"][i]) for i in Regions if not i.isascii()]
	for l in locales:
		if l.region.flag in flags:
			continue
		l.states_to_run = [i for i in states if i in l.states_to_run]
	await AsyncGather((locale.main(session) for locale in locales), limit = 3)
	arrival = sorted(((store, locale.position) for locale in locales
		for store in locale.new_stores if locale.position), key = lambda t: t[1])
	if arrival and not args.local:
		logger.info(f"[推送通知] {len(arrival)} 家新零售店")
		title = ["\\#新店新机遇", "已开始招聘", ""]
		body = [f"{disMarkdown(s.telename)} [↗]({p.url})" for s, p in arrival]
		image = "https://www.apple.com/careers/images/retail/fy22/hero_hotspot/default@2x.png"
		push = {"mode": "photo-text", "text": "\n".join(title + body),
			"chat_id": chat_ids[0], "parse": "MARK", "image": image}
		await async_post(push)
	save_db(db, locales)

async def position(flags: list[str], managed: Optional[bool], session: SessionType) -> None:
	db = load_db()
	locales = [Locale(Regions[i], db["regions"][i]) for i in flags if i in Regions]
	for locale in locales:
		saved = [p.id for p in locale.positions]
		later_than = (n := datetime.now()).replace(year = n.year - 1).strftime("%F")
		positions = await locale.fetch_positions(managed = managed,
			filters = RETAIL_FILTER, later_than = later_than, session = session)
		if not positions:
			logger.log(19, f"[没有职位] {locale.region.name}")
			continue
		for pos in positions:
			if pos.id in saved:
				logging.log(18, f"[已知职位] {pos.id}: {pos.title}, {pos.location}, {pos.update}")
				continue
			logging.info(f"[职位] {pos.id}: {pos.title}, {pos.location}, {pos.update}")
		if managed is not False:
			locale.updated = True
			locale.positions = [p for p in positions if p.managed]
	save_db(db, locales)

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	set_logger(args.verbose, args.debug)
	logger.info("程序启动")
	if not args.args:
		flags, states = [i for i in Regions if not i.isascii()], []
	else:
		states = [i for i in args.args if i.startswith("state")]
		flags = [i for i in args.args if i in Regions]
	if any((args.position, args.retail, args.standalone)):
		await position(flags, managed = None if args.retail else args.position, session = session)
	else:
		await entry(flags, states, session)
	logger.info("程序结束")

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("args", type = str, nargs = "*", help = "指定地区或行政区")
	mode_group = parser.add_mutually_exclusive_group()
	mode_group.add_argument("-p", "--position", action = "store_true", help = "寻找普通职位模式")
	mode_group.add_argument("-r", "--retail", action = "store_true", help = "寻找所有职位模式")
	mode_group.add_argument("-s", "--standalone", action = "store_true", help = "寻找独立职位模式")
	parser.add_argument("-d", "--debug", action = "store_true", help = "打印调试信息")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "记录调试信息")
	args = parser.parse_args()
	asyncio.run(main(args))