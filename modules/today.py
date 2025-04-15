import asyncio
import json
import re
from datetime import datetime
from typing import Any, Literal, Optional, Self, Sequence
from zoneinfo import ZoneInfo

from modules.regions import Regions
from modules.util import (AsyncGather, CoroutineType, SemaphoreType,
                          SessionType, browser_agent, get_session, request,
                          with_semaphore)
from storeInfo import Store as Raw_Store
from storeInfo import getStore as getRaw_Store
from storeInfo import storeReturn

ACCEPT = ["jpg", "png", "mp4", "mov", "pages", "key", "pdf"]
PARAM = {"method": "GET", "timeout": 25, "retry": 5}
SEMAPHORE_LIMIT = 20
VALIDDATES = r"(-([0-9]{4,8}))$"

GRAPH: dict[str, list[str]] = {}
LEADERBOARD: dict[str, int] = {}

todayNation = {v.url_taa: k for k, v in Regions.items() if v.url_taa is not None}

class APIClass:
	args = {
		"COLLECTIONSLUG": "collectionSlug",
		"COURSESLUG": "courseSlug",
		"ROOTPATH": "stageRootPath",
		"SCHEDULEID": "scheduleId",
		"STORESLUG": "storeSlug"}

	def __init__(self, parts: Sequence[str]) -> None:
		self._parts: list[str] = list(parts)

	def __getitem__(self, key: str) -> Self:
		return type(self)(parts = self._parts + [key])

	def __repr__(self) -> str:
		return "/".join(self._parts)

	def format(self, **kwargs) -> str:
		return "/".join(self._parts) + "?" + "&".join(f"{self.args.get(k, k)}={v}" for k, v in kwargs.items())

API = APIClass("https://www.apple.com/today-bff".split("/"))

def GenerateLeaderboard(db_filename: str) -> dict[int, list[str]]:
	import math

	from modules.michael import Store, loads

	def calculate_bonus(store: Store) -> int:
		bonus = 0
		if store.forum:
			bonus += 10
		if store.type == "Vintage D":
			bonus += 5
		for key in ("outdoor", "trees", "boardroom"):
			if getattr(store, key):
				bonus += 3
		for event in store.events:
			if getattr(event, "art", None):
				bonus += 2
			if val := getattr(event, "gallery", None):
				bonus += math.ceil(math.log2(val))
			if val := getattr(event, "pr", None):
				bonus += 2 * len(val.split(","))
		return bonus

	db = loads(db_filename)
	for rid, store in db.items():
		LEADERBOARD[f"R{rid}"] = calculate_bonus(store)
	return {point: sorted(k for k, v in LEADERBOARD.items() if v == point)
		for point in sorted(set(LEADERBOARD.values()))}

def KnownSlugs() -> list[str]:
	try:
		with open("Retail/assured-events.json") as r:
			assure = json.load(r)
		return list(assure.values())
	except FileNotFoundError:
		return []

def ParseResolution(vids: list[str], direction: Optional[Literal["l", "p"]] = None) -> list[str]:
	res = {}
	for v in vids:
		f = re.findall(r"([0-9]+)x([0-9]+)\.[a-zA-Z0-9]+", v)
		if not f:
			return vids
		res[v] = [int(f[0][0]), int(f[0][1])]
	vids.sort(key = lambda k: res[k][0] * res[k][1], reverse = True)

	if direction not in ["p", "l"]:
		return vids
	return [i for i in vids if direction == "p" and res[i][0] < res[i][1]
		or direction == "l" and res[i][0] > res[i][1]]

def Peers(stores: list[Raw_Store], fast: bool = False) -> list[Raw_Store]:
	if not fast:
		return stores
	try:
		from modules.dominating import get_dominating_set
		if not GRAPH:
			with open("Retail/taa-graph.json") as r:
				GRAPH.update(json.load(r))
	except Exception:
		return stores
	try:
		if not LEADERBOARD:
			GenerateLeaderboard("Retail/facades.json")
	except Exception:
		pass
	results: dict[str, list[str]] = {}
	mapping = {s.rid: s for s in stores}
	subgraph = {s: GRAPH.get(s, []) for s in mapping}
	sets = [get_dominating_set(subgraph, store) for store in mapping]
	sets.sort(key = lambda s: (len(s), -sum(LEADERBOARD.get(store, 0) for store in s)))
	results.update({a: GRAPH.get(a, []) for a in sorted(sets[0])})
	return [i for i in [getRaw_Store(s) for s in results] if i]

def Space(text: str) -> str:
	rep = {0xa0: 0x20, 0x200b: None, 0x200c: None, 0x2060: None}
	return text.translate(rep)

def ValidDates(ex: str, runtime: datetime) -> list[datetime]:
	v = []
	match len(ex):
		case 4:
			ex += str(runtime.year)
			possible = ["%m%d%Y", "%d%m%Y"]
		case 6:
			possible = ["%y%m%d", "%d%m%y", "%m%d%y"]
		case 8:
			possible = ["%Y%m%d", "%d%m%Y", "%m%d%Y"]
		case _:
			return []
	for pattern in possible:
		try:
			date = datetime.strptime(ex, pattern).date()
		except ValueError:
			pass
		else:
			delta = (date - runtime.date()).days
			if date not in v and delta > -7 and delta < 70:
				v.append(date)
	return v

class TodayObject:
	hashattr: list[str] = []
	sortkeys: list[str] = []
	raw: dict[str, Any] = {}

	def _sort_tuple(self) -> tuple[Any, ...]:
		return tuple(getattr(self, key) for key in self.sortkeys)

	def __hash__(self) -> int:
		return hash((self.__class__.__name__, *(getattr(self, attr) for attr in self.hashattr)))

	def __lt__(self, other) -> bool:
		return type(other) is type(self) and self._sort_tuple() < other._sort_tuple()

	def __gt__(self, other) -> bool:
		return type(other) is type(self) and self._sort_tuple() > other._sort_tuple()

	def __eq__(self, other) -> bool:
		return type(other) is type(self) and self._sort_tuple() == other._sort_tuple()

class TodayEncoder(json.JSONEncoder):
	def __init__(self, **kwargs) -> None:
		k = {**kwargs, "ensure_ascii": False}
		super().__init__(**k)

	def default(self, o) -> dict[str, Any]:
		if isinstance(o, TodayObject) or isinstance(o, Raw_Store):
			return o.raw
		return super().default(o)

class Store(TodayObject):
	hashattr: list[str] = ["sid"]
	sortkeys: list[str] = ["raw_store"]

	def __init__(self,
		raw: Optional[dict[str, Any]] = None,
		rootPath: Optional[str] = None,
		sid: Optional[int | str] = None,
		store: Optional[Raw_Store] = None) -> None:

		assert raw or sid or store, "raw, sid, store 至少提供一个"
		if raw:
			self.name: str = raw["name"]
			self.sid: str = raw["storeNum"]
			raw_store = getRaw_Store(self.sid)
			assert raw_store is not None, f"本地数据库中无法匹配关键字 {sid!r}"
			self.raw_store: Raw_Store = raw_store
			self.timezone: str = raw["timezone"]["name"]
			self.slug: str = raw["slug"]
			assert (rp := rootPath or self.raw_store.region.url_taa) is not None, "rootPath 无效"
			self.rootPath: str = rp
			self.flag: str = todayNation[self.rootPath]
			self.url: str = f"https://www.apple.com{".cn" if self.rootPath == "/cn" else ""}{raw["path"]}"
			self.coord: Optional[list[float]] = [raw["lat"], raw["long"]]
		else:
			temp = store or (getRaw_Store(sid) if sid else None)
			assert temp is not None, f"本地数据库中无法匹配关键字 {sid!r}"
			self.raw_store: Raw_Store = temp
			self.sid: str = self.raw_store.rid
			self.name: str = self.raw_store.name
			assert self.raw_store.slug and self.raw_store.url, "本地数据库信息不正确"
			self.slug: str = self.raw_store.slug
			assert (rp := rootPath or self.raw_store.region.url_taa) is not None, "rootPath 无效"
			self.rootPath: str = rp
			assert self.raw_store.timezone, "本地数据库时区不正确"
			self.timezone: str = self.raw_store.timezone.key
			self.flag: str = todayNation[self.rootPath]
			self.url: str = self.raw_store.url
			self.coord: Optional[list[float]] = None
		self.today: str = self.url.replace("/retail/", "/today/")
		self.calendar: str = self.url.replace("/retail/", "/today/calendar/")
		self.serial: dict[str, str] = {"sid": self.sid}
		self.raw: dict[str, Any] = {k: v for k, v in vars(self).items() if k != "raw"}

	def __repr__(self) -> str:
		return f'<Store "{self.name}" ({self.sid}), "{self.slug}", "{self.rootPath}">'

	async def getCourses(self, ensure: bool = True, session: Optional[SessionType] = None) -> list["Course"]:
		try:
			nearby = {"nearby": "true"} if not ensure else {}
			r = await request(session = session, headers = browser_agent,
				url = (API["landing"]["store" if ensure else "nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath, **nearby), **PARAM)
			remote = json.loads(Space(r))
			assert "courses" in remote
		except:
			raise ValueError(f"获取 {self.sid} 数据失败") from None
		return await AsyncGather(Course.get(rootPath = self.rootPath,
			slug = c["urlTitle"], remote = remote, session = session)
			for c in remote["courses"].values())

	async def getSchedules(self, ensure: bool = True,
		date: Optional[datetime] = None,
		covered_store_list: Optional[list[str]] = None,
		session: Optional[SessionType] = None) -> list["Schedule"]:
		try:
			nearby = {"nearby": "true"} if not ensure else {}
			r = await request(session = session, headers = browser_agent,
				url = (API["landing"]["store" if ensure else "nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath, **nearby), **PARAM)
			remote = json.loads(Space(r))
			assert "schedules" in remote
		except:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks: list[CoroutineType[Schedule]] = []
		for i, s in remote["schedules"].items():
			storeNum = s["storeNum"]
			course = remote["courses"][s["courseId"]]
			if not ensure or storeNum == self.sid or "VIRTUAL" in course["type"]:
				if s["courseId"] not in remote["courses"]:
					continue
				tasks.append(Schedule.get(rootPath = self.rootPath, scheduleId = i,
					slug = course["urlTitle"], remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [i for i in results if i.rawStart.date() == date.date()]
		if covered_store_list is not None:
			covered_store_list.clear()
			covered_store_list.extend(remote["stores"])
		return results

	async def getCoord(self, session: Optional[SessionType] = None) -> list[float]:
		d = await self.raw_store.detail(session = session)
		self.coord = [i[1] for i in sorted(d["geolocation"].items())]
		return self.coord

	async def getCovering(self, graph: dict[str, list[str]] = {}) -> list[str]:
		results: list[str] = []
		_ = await self.getSchedules(ensure = False, covered_store_list = results)
		results = sorted(r for r in results if (s := getRaw_Store(r)) and s.isOpen)
		graph[self.sid] = results
		return results

class Talent(TodayObject):
	hashattr: list[str] = ["name"]
	sortkeys: list[str] = ["name"]

	def __init__(self, raw: dict[str, Any]) -> None:
		self.raw: dict[str, Any] = raw
		self.name: str = raw["name"].strip()
		self.title: Optional[str] = raw["title"].strip() if "title" in raw else None
		self.description: Optional[str] = re.sub(r"\s*\n\s*", " ", raw["description"].strip()) if "description" in raw else None
		self.image: Optional[str] = raw.get("backgroundImage") or raw.get("logo")
		self.links: dict[str, str] = (
			({"website": raw["websiteUrl"]} if "websiteUrl" in raw else {}) |
			({"url": raw["url"]} if "url" in raw else {}) |
			({social["name"]: social["url"] for social in raw.get("socialLinks", {})}))

	def __repr__(self) -> str:
		return f'<Talent "{self.name}"' + (f', "{self.title}"' if self.title else "") + ">"

class Course(TodayObject):
	hashattr: list[str] = ["rootPath", "slug"]
	sortkeys: list[str] = ["courseId", "rootPath"]

	@classmethod
	async def get(cls,
		rootPath: str,
		slug: str,
		remote: Optional[dict[str, Any]] = None,
		session: Optional[SessionType] = None) -> Self:
		if remote is None:
			try:
				r = await request(session = session, headers = browser_agent,
					url = API["session"]["course"].format(
					COURSESLUG = slug, ROOTPATH = rootPath), **PARAM)
				remote = json.loads(Space(r))
				assert isinstance(remote, dict) and "courses" in remote
			except:
				raise ValueError(f"获取课程 {rootPath}/{slug} 数据失败") from None

		assert isinstance(remote, dict), f"课程 {rootPath}/{slug} 数据信息无效"
		courseId: str = next(t[0] for t in remote["courses"].items() if t[1]["urlTitle"] == slug)
		talents: list[dict[str, Any]] = remote.get("talents", [])
		raw: dict[str, Any] = remote["courses"][courseId]
		moreAbout, collection = [], raw.get("collectionName")
		if "moreAbout" in remote:
			moreAbout.append(remote["moreAbout"])
		if "heroGallery" in remote:
			for m in remote["heroGallery"]:
				if m.get("heroType") == "TAG":
					moreAbout.append(m)
		for more in moreAbout:
			if collection and any(collection == more.get(k, k) for k in ["title", "name"]):
				collection = await Collection.get(rootPath = rootPath, slug = more["collId"], session = session)

		return cls(courseId = courseId, raw = raw, rootPath = rootPath, collection = collection, talents = talents)

	def __init__(self,
		courseId: str,
		raw: dict[str, Any],
		rootPath: str,
		collection: Optional["str | Collection"] = None,
		talents: list[dict[str, Any]] = []) -> None:

		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.courseId: str = courseId
		self.name: str = raw["name"].strip()
		self.title: str = raw["title"]
		self.slug: str = raw["urlTitle"]
		self.serial: dict[str, str] = {"slug": self.slug, "rootPath": self.rootPath}
		self.collection: Optional[str | Collection] = collection

		self.description: dict[str, str] = {
			"long": raw["longDescription"].strip(),
			"medium": raw["mediumDescription"].strip(),
			"short": raw["shortDescription"].strip()}
		for k, v in self.description.items():
			self.description[k] = re.sub(r"\s*\n\s*", " ", v)

		self.intro: dict[str, str | list[str]] = {}
		if "modalVideo" in raw:
			self.intro = {
				"poster": raw["modalVideo"]["poster"]["source"],
				"video": ParseResolution(raw["modalVideo"]["sources"])}

		media = raw["backgroundMedia"]
		self.images: dict[str, str] = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]}
		self.videos: dict[str, dict[str, str | list[str]]] = {}
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"videos": ParseResolution(media["ambientVideo"]["sources"], "p")},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": ParseResolution(media["ambientVideo"]["sources"], "l")}}

		self.virtual: bool = "VIRTUAL" in raw["type"]
		self.special: bool = "SPECIAL" in raw["type"] or "HIGH" in raw["talentType"]
		self.talents: list[Talent] = [Talent(raw = t) for t in talents] if talents else []
		self.url: str = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}"
		self.raw: dict = raw | {"serial": self.serial}

	def __repr__(self) -> str:
		col = (f', Collection <{self.collection.name}>' if isinstance(self.collection, Collection) \
			else f', Collection "{self.collection}"') if self.collection is not None else ""
		return f'<Course {self.courseId} "{self.name}", "{self.slug}"{col}>'

	def elements(self, accept: Optional[list[str]] = None) -> list[str]:
		accept = accept or ACCEPT
		result, pattern = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + pattern +
			"))+[\'\"]?", json.dumps(self, cls = TodayEncoder)) if i[0] not in result]
		return result

	async def getSchedules(self, store: Store, ensure: bool = True,
		date: Optional[datetime] = None,
		session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list["Schedule"]:
		try:
			async with with_semaphore(semaphore):
				r = await request(session = session, headers = browser_agent,
					url = (API["session"]["course"]["store" if ensure else "nearby"]).format(
					STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath), **PARAM)
			remote = json.loads(Space(r))
			assert "schedules" in remote
		except:
			raise ValueError(f"获取排课 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks: list[CoroutineType[Schedule]] = []
		schedules = remote["schedules"]
		for i in remote["schedules"]:
			storeNum = schedules[i]["storeNum"]
			if schedules[i]["courseId"] == self.courseId:
				if not ensure or storeNum == store.sid or "VIRTUAL" in remote["courses"][self.courseId]["type"]:
					tasks.append(Schedule.get(rootPath = store.rootPath,
						scheduleId = i, slug = self.slug, remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [i for i in results if i.rawStart.date() == date.date()]
		return results

	async def getMultipleSchedules(self,
		raw_stores: list[Raw_Store] = [],
		stores: list[Store] = [],
		date: Optional[datetime] = None, fast: bool = True,
		session: Optional[SessionType] = None) -> list["Schedule"]:
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		if raw_stores:
			stores = [Store(store = i) for i in raw_stores]
		elif stores:
			raw_stores = [i.raw_store for i in stores]
		async with get_session(session) as session:
			tasks = (self.getSchedules(Store(store = i), ensure = not fast,
				date = date, session = session, semaphore = semaphore) for i in Peers(raw_stores, fast))
			results = await AsyncGather(tasks, return_exceptions = True)
		return sorted(k for k in {i for j in (r for r in results if not isinstance(r, Exception))
			for i in j} if k.raw_store in raw_stores)

	async def getSingleSchedule(self, session: Optional[SessionType] = None) -> "Schedule":
		return await Schedule.get(scheduleId = self.courseId, rootPath = self.rootPath, slug = self.slug, session = session)

class Schedule(TodayObject):
	hashattr: list[str] = ["rootPath", "scheduleId", "slug"]
	sortkeys: list[str] = ["rawStart", "scheduleId"]

	@classmethod
	async def get(cls,
		rootPath: str,
		scheduleId: str,
		slug: str,
		remote: Optional[dict[str, Any]] = None,
		session: Optional[SessionType] = None) -> Self:
		if remote is None:
			scheduleId = str(scheduleId)
			try:
				r = await request(session = session, headers = browser_agent,
					url = API["session"]["schedule"].format(
					COURSESLUG = slug, SCHEDULEID = scheduleId, ROOTPATH = rootPath), **PARAM)
				remote = json.loads(Space(r))
				assert isinstance(remote, dict) and "schedules" in remote
			except:
				raise ValueError(f"获取排课 {rootPath}/{slug}/{scheduleId} 数据失败") from None

		assert isinstance(remote, dict), f"排课 {rootPath}/{slug}/{scheduleId} 数据信息无效"
		store = Store(
			sid = remote["schedules"][scheduleId]["storeNum"],
			raw = remote["stores"].get(remote["schedules"][scheduleId]["storeNum"]),
			rootPath = rootPath)
		cid = remote["schedules"][scheduleId]["courseId"]
		course = await Course.get(rootPath = rootPath,
			slug = remote["courses"][cid]["urlTitle"],
			remote = remote, session = session)
		raw: dict[str, Any] = remote["schedules"][scheduleId]

		return cls(scheduleId = scheduleId, course = course, store = store, rootPath = rootPath, raw = raw)

	def __init__(self,
		course: Course,
		scheduleId: str,
		store: Store,
		raw: dict[str, Any],
		rootPath: str) -> None:

		_ = [setattr(self, key, getattr(course, key)) for key in vars(course)]
		self.slug = course.slug
		self.course: Course = course
		self.scheduleId = scheduleId
		self.rootPath = rootPath
		self.flag = todayNation[self.rootPath]
		self.serial = {"slug": self.slug, "scheduleId": scheduleId, "rootPath": self.rootPath}

		self.store = store
		self.raw_store = self.store.raw_store
		self.timezone = store.timezone
		self.tzinfo = ZoneInfo(self.timezone)
		self.timeStart = datetime.fromtimestamp(raw["startTime"] / 1000, tz = self.tzinfo)
		self.timeEnd = datetime.fromtimestamp(raw["endTime"] / 1000, tz = self.tzinfo)
		self.rawStart = self.timeStart.replace(tzinfo = None)
		self.rawEnd = self.timeEnd.replace(tzinfo = None)
		self.status: bool = raw["status"] == "RSVP"
		self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}/{scheduleId}/?sn={self.store.sid}"
		self.raw: dict[str, Any] = raw | {"serial": self.serial}

	def datetimeStart(self, form: str = "%-m 月 %-d 日 %-H:%M") -> str:
		return f"{self.timeStart or self.rawStart:{form}}"

	def datetimeEnd(self, form: str = "%-H:%M") -> str:
		return f"{self.timeEnd or self.rawEnd:{form}}"

	def __repr__(self) -> str:
		loc = self.store.sid if not self.course.virtual else "Online"
		return f'<Schedule {self.scheduleId} of {self.course.courseId}, {self.datetimeStart("%-m/%-d %-H:%M")}-{self.datetimeEnd()} @ {loc}>'

class Collection(TodayObject):
	hashattr: list[str] = ["rootPath", "slug"]
	sortkeys: list[str] = ["rootPath", "slug"]

	@classmethod
	async def get(cls,
		rootPath: str,
		slug: str,
		remote: Optional[dict[str, Any]] = None,
		session: Optional[SessionType] = None) -> Self:
		if remote is None:
			try:
				r = await request(session = session, headers = browser_agent,
					url = API["collection"]["geo"].format(
					COLLECTIONSLUG = slug, ROOTPATH = rootPath), **PARAM)
				remote = json.loads(Space(r))
			except:
				raise ValueError(f"获取系列 {rootPath}/{slug} 数据失败") from None

		assert isinstance(remote, dict), f"系列 {rootPath}/{slug} 数据信息无效"
		return cls(rootPath = rootPath, slug = slug, raw = remote)

	def __init__(self,
		raw: dict[str, Any],
		rootPath: str,
		slug: str) -> None:

		self.name: str = raw["name"].strip()
		self.slug: str = slug
		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.url: str = f"https://www.apple.com{rootPath.replace('/cn', '.cn')}/today/collection/{slug}/"
		self.serial: dict[str, str] = {"slug": slug, "rootPath": rootPath}

		self.description: dict[str, str] = {
			"long": raw["longDescription"].strip(),
			"medium": raw["mediumDescription"].strip(),
			"short": raw["shortDescription"].strip()}
		for k, v in self.description.items():
			self.description[k] = re.sub(r"\s*\n\s*", " ", v)

		media = raw["heroGallery"][0]["backgroundMedia"]
		self.images: dict[str, str] = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]}
		self.videos: dict[str, dict[str, str | list[str]]] = {}
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"videos": ParseResolution(media["ambientVideo"]["sources"], "p")},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": ParseResolution(media["ambientVideo"]["sources"], "l")}}

		self.talents: list[Talent]
		if "inCollaborationWith" in raw:
			self.talents = [Talent(raw = t) for t in raw["inCollaborationWith"]["partners"]]
		else:
			self.talents = []
		self.raw: dict[str, Any] = raw | {"serial": self.serial}

	def __repr__(self) -> str:
		return f'<Collection "{self.name}", "{self.slug}", "{self.rootPath}">'

	def elements(self, accept: Optional[list[str]] = None) -> list[str]:
		accept = accept or ACCEPT
		result, pattern = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + pattern +
			"))+[\'\"]?", json.dumps(self, cls = TodayEncoder)) if i[0] not in result]
		return result

	async def getSchedules(self, store: Store, ensure: bool = True,
		date: Optional[datetime] = None,
		session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> list[Schedule]:
		try:
			async with with_semaphore(semaphore):
				r = await request(session = session, headers = browser_agent,
					url = (API["collection"]["store" if ensure else "nearby"]).format(
					STORESLUG = store.slug, COLLECTIONSLUG = self.slug, ROOTPATH = store.rootPath), **PARAM)
			remote = json.loads(Space(r))
			assert "schedules" in remote
		except:
			raise ValueError(f"获取排课 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks: list[CoroutineType[Schedule]] = []
		for i, s in remote["schedules"].items():
			courseId, storeNum = s["courseId"], s["storeNum"]
			course = remote["courses"][courseId]
			if self.slug in (m["collId"] for m in remote["heroGallery"] if m["heroType"] == "TAG"):
				if not ensure or storeNum == store.sid or "VIRTUAL" in course["type"]:
					tasks.append(Schedule.get(rootPath = store.rootPath, scheduleId = i,
						slug = course["urlTitle"], remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [i for i in results if i.rawStart.date() == date.date()]
		return results

	async def getMultipleSchedules(self,
		raw_stores: list[Raw_Store] = [],
		stores: list[Store] = [],
		date: Optional[datetime] = None, fast: bool = True,
		session: Optional[SessionType] = None) -> list[Schedule]:
		return await Course.getMultipleSchedules(self, # type: ignore
			raw_stores = raw_stores, stores = stores,
			date = date, fast = fast, session = session)

	async def getCourses(self, rootPath: Optional[str] = None, fast: bool = False,
		session: Optional[SessionType] = None) -> list[Course]:
		stores = storeReturn(todayNation[rootPath or self.rootPath], opening = True)
		schedules = await self.getMultipleSchedules(stores, fast = fast, session = session)
		return sorted({schedule.course for schedule in schedules})

class Sitemap(TodayObject):
	hashattr: list[str] = ["urlPath"]
	sortkeys: list[str] = ["urlPath"]

	def match_by_assure(self, slug: str) -> bool:
		for s in KnownSlugs():
			if s == slug:
				return False
		return True

	def match_by_valid(self, slug: str) -> bool:
		matches = re.findall(VALIDDATES, slug)
		return bool(matches and ValidDates(matches[0][1], self.runtime) != [])

	def __init__(self, rootPath: Optional[str] = None, flag: Optional[str] = None) -> None:
		assert rootPath is not None or flag, "rootPath 和 flag 必须提供一个"
		match rootPath, flag:
			case _, fl if fl is not None:
				self.urlPath = Regions[fl].url_retail
			case rp, _ if rp is not None:
				self.urlPath = rp.replace("/cn", ".cn")
		self.using = self.match_by_valid if not KnownSlugs() else self.match_by_assure
		self.runtime = datetime.now()
		self.raw = {"urlPath": self.urlPath}

	def __repr__(self) -> str:
		return f'<Sitemap "{self.urlPath}">'

	async def getURLs(self, session: Optional[SessionType] = None) -> list[str]:
		try:
			r = await request(f"https://www.apple.com{self.urlPath}/today/sitemap.xml",
				session = session, headers = browser_agent, **PARAM)
			urls = re.findall(r"<loc>\s*(\S*)\s*</loc>", r)
		except:
			raise ValueError(f"获取 {self.urlPath!r} Sitemap 数据失败") from None

		slugs = {}
		for url in urls:
			if "/event/" not in url:
				continue
			slug = url.split("/event/")[1].split("/")[0].split("?")[0]
			if self.using(slug):
				slugs[slug] = slugs.get(slug, []) + [url]

		objects = []
		for slug in slugs:
			slugs[slug].sort()
			if self.using == self.match_by_valid or self.match_by_valid(slug):
				parsing = slugs[slug][1 if len(slugs[slug]) > 1 else 0]
			else:
				parsing = slugs[slug][0]
			objects.append(parsing)
		return objects

	async def getObjects(self, extend_schedule: bool = False,
		session: Optional[SessionType] = None) -> list[Collection | Course | Schedule]:
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as session:
			results = await AsyncGather((getURL(u, session = session, semaphore = semaphore)
				for u in await self.getURLs()), return_exceptions = True)
			results = [i for i in results if not isinstance(i, Exception)]
			if extend_schedule:
				extend = []
				avail = [i.scheduleId for i in results if isinstance(i, Schedule)]
				for inst in results:
					try:
						assert isinstance(inst, Course)
						assert inst.special
						assert inst.courseId not in avail
						schedule = await inst.getSingleSchedule(session = session)
						extend.append(schedule)
					except Exception:
						pass
				results.extend(extend)
		return results

def parseURL(url: str) -> dict[str, str]:
	cp = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*))"
	sp = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*)/([67][0-9]{18})(\/\?sn\=(R[0-9]{3}))?)"
	lp = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/collection/([a-z0-9\-]*))(/\S*)?"

	match [re.findall(p, url, re.I) for p in [sp, cp, lp]]:
		case [[s, *_], _, _]:
			return {
				"type": "schedule", "rootPath": s[1].replace(".cn", "/cn"),
				"slug": s[2], "scheduleId": s[3], "sid": s[5],
				"url": f"https://www.apple.com{s[1]}/today/event/{s[2]}/{s[3]}/?sn={s[5]}"}
		case [_, [c, *_], _]:
			return {
				"type": "course", "rootPath": c[1].replace(".cn", "/cn"),
				"slug": c[2], "url": f"https://www.apple.com{c[1]}/today/event/{c[2]}"}
		case [_, _, [l, *_]]:
			return {
				"type": "collection", "rootPath": l[1].replace(".cn", "/cn"),
				"slug": l[2], "url": f"https://www.apple.com{l[1]}/today/collection/{l[2]}"}
	return {}

async def generateGraph(stores: list[Store], graph: dict[str, list[str]] = {},
	retry: int = 3, limit: int = 10) -> dict[str, list[str]]:
	while retry and stores:
		retry -= 1
		await AsyncGather((store.getCovering(graph) for store in stores),
			limit = limit, return_exceptions = True)
		stores = [store for store in stores if store.sid not in graph]
	for s in stores:
		graph[s.sid] = []
	with open("Retail/taa-graph.json", "w") as w:
		json.dump(graph, w, ensure_ascii = False, indent = 2, sort_keys = True)
	return graph

async def getURL(url: str,
	session: Optional[SessionType] = None,
	semaphore: Optional[SemaphoreType] = None) -> Collection | Course | Schedule:
	async with with_semaphore(semaphore):
		match parseURL(url):
			case {"type": "schedule", "rootPath": r, "slug": g, "scheduleId": s}:
				return await Schedule.get(rootPath = r, scheduleId = s, slug = g, session = session)
			case {"type": "course", "rootPath": r, "slug": g}:
				return await Course.get(rootPath = r, slug = g, session = session)
			case {"type": "collection", "rootPath": r, "slug": g}:
				return await Collection.get(rootPath = r, slug = g, session = session)
	raise ValueError(f"无法解析并生成自: {url}")