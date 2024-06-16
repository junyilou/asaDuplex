import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Literal, Optional, Self, Sequence
from zoneinfo import ZoneInfo

from modules.regions import Regions
from modules.util import (AsyncGather, CoroutineType, SemaphoreType,
                          SessionType, browser_agent, disMarkdown, get_session,
                          request, tz_text, with_semaphore)
from storeInfo import Store as Raw_Store
from storeInfo import getStore as getRaw_Store
from storeInfo import storeReturn

ACCEPT = ["jpg", "png", "mp4", "mov", "pages", "key", "pdf"]
PARAM = {"method": "GET", "timeout": 25, "retry": 5}
SEMAPHORE_LIMIT = 20
VALIDDATES = r"(-([0-9]{4,8}))$"
todayNation = {v.url_taa: k for k, v in Regions.items()}

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

class utils:
	@staticmethod
	def get_fas_stores(rootPath: str, fast: bool) -> list[Raw_Store]:
		try:
			assert fast
			with open("Retail/findasession-stores.json") as r:
				fas = json.load(r)
			return [s for s in (getRaw_Store(i) for i in fas[todayNation[rootPath]]) if s]
		except:
			return storeReturn(todayNation[rootPath], opening = True)

	@staticmethod
	def known_slugs() -> list[str]:
		try:
			with open("Retail/assured-events.json") as r:
				assure = json.load(r)
			return list(assure.values())
		except FileNotFoundError:
			return []

	@staticmethod
	def resolution(vids: list[str], direction: Optional[Literal["l", "p"]] = None) -> list[str]:
		res = {}
		for v in vids:
			f = re.findall(r"([0-9]+)x([0-9]+)\.[a-zA-Z0-9]+", v)
			if not f:
				return vids
			res[v] = [int(f[0][0]), int(f[0][1])]
		vids.sort(key = lambda k: res[k][0] * res[k][1], reverse = True)

		if direction not in ["p", "l"]:
			return vids
		return [i for i in vids if direction == "p" and res[i][0] < res[i][1] \
			or direction == "l" and res[i][0] > res[i][1]]

	@staticmethod
	def separate(text: str) -> str:
		rep = {0xa0: 0x20, 0x200b: None, 0x200c: None, 0x2060: None}
		return text.translate(rep)

	@staticmethod
	def valid_dates(ex: str, runtime: datetime) -> list[datetime]:
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
			self.rootPath: str = rootPath or self.raw_store.region.url_taa
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
			self.rootPath: str = rootPath or self.raw_store.region.url_taa
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
			remote = json.loads(utils.separate(r))
			assert "courses" in remote
		except:
			raise ValueError(f"获取 {self.sid} 数据失败") from None
		return await AsyncGather(Course.get(rootPath = self.rootPath,
			slug = c["urlTitle"], remote = remote, session = session)
			for c in remote["courses"].values())

	async def getSchedules(self, ensure: bool = True,
		date: Optional[datetime] = None,
		session: Optional[SessionType] = None) -> list["Schedule"]:
		try:
			nearby = {"nearby": "true"} if not ensure else {}
			r = await request(session = session, headers = browser_agent,
				url = (API["landing"]["store" if ensure else "nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath, **nearby), **PARAM)
			remote = json.loads(utils.separate(r))
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
		return results

	async def getCoord(self, session: Optional[SessionType] = None) -> list[float]:
		d = await self.raw_store.detail(mode = "raw", session = session)
		assert isinstance(d, dict)
		self.coord = [i[1] for i in sorted(d["geolocation"].items())]
		return self.coord

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
				remote = json.loads(utils.separate(r))
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
				"video": utils.resolution(raw["modalVideo"]["sources"])}

		media = raw["backgroundMedia"]
		self.images: dict[str, str] = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]}
		self.videos: dict[str, dict[str, str | list[str]]] = {}
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"videos": utils.resolution(media["ambientVideo"]["sources"], "p")},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": utils.resolution(media["ambientVideo"]["sources"], "l")}}

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
			remote = json.loads(utils.separate(r))
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

	async def getRootSchedules(self, rootPath: Optional[str] = None,
		date: Optional[datetime] = None, fast: bool = False,
		session: Optional[SessionType] = None) -> list["Schedule"]:
		rootPath = rootPath or self.rootPath
		stores = utils.get_fas_stores(rootPath, fast)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as session:
			tasks = (self.getSchedules(Store(store = i, rootPath = rootPath),
				ensure = not fast, date = date, session = session, semaphore = semaphore) for i in stores)
			results = await AsyncGather(tasks, return_exceptions = True)
		return sorted({i for j in (r for r in results if not isinstance(r, BaseException)) for i in j})

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
				remote = json.loads(utils.separate(r))
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
		self.scheduleId: str = scheduleId
		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.serial: dict[str, str] = {"slug": self.slug, "scheduleId": scheduleId, "rootPath": self.rootPath}

		self.store: Store = store
		self.raw_store: Raw_Store = self.store.raw_store
		self.timezone: str = store.timezone
		try:
			self.tzinfo: Optional[ZoneInfo] = ZoneInfo(self.timezone)
			self.timeStart: Optional[datetime] = datetime.fromtimestamp(raw["startTime"] / 1000, self.tzinfo)
			self.timeEnd: Optional[datetime] = datetime.fromtimestamp(raw["endTime"] / 1000, self.tzinfo)
		except:
			self.tzinfo = self.timeStart = self.timeEnd = None
		self.rawStart: datetime = datetime.fromtimestamp(raw["startTime"] / 1000)
		self.rawEnd: datetime = datetime.fromtimestamp(raw["endTime"] / 1000)
		self.status: bool = raw["status"] == "RSVP"
		self.url: str = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}/{scheduleId}/?sn={self.store.sid}"
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
				remote = json.loads(utils.separate(r))
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
					"videos": utils.resolution(media["ambientVideo"]["sources"], "p")},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": utils.resolution(media["ambientVideo"]["sources"], "l")}}

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
			remote = json.loads(utils.separate(r))
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

	async def getRootSchedules(self, rootPath: Optional[str] = None,
		date: Optional[datetime] = None, fast: bool = False,
		session: Optional[SessionType] = None) -> list[Schedule]:
		rootPath = rootPath or self.rootPath
		stores = utils.get_fas_stores(rootPath, fast)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as session:
			tasks = (self.getSchedules(Store(store = i, rootPath = rootPath),
				ensure = not fast, date = date, session = session, semaphore = semaphore) for i in stores)
			results = await AsyncGather(tasks, return_exceptions = True)
		return sorted({i for j in (r for r in results if not isinstance(r, BaseException)) for i in j})

	async def getCourses(self, rootPath: Optional[str] = None, fast: bool = False,
		session: Optional[SessionType] = None) -> list[Course]:
		schedules = await self.getRootSchedules(rootPath = rootPath, fast = fast, session = session)
		return sorted({schedule.course for schedule in schedules})

class Sitemap(TodayObject):
	hashattr: list[str] = ["urlPath"]
	sortkeys: list[str] = ["urlPath"]

	def match_by_assure(self, slug: str) -> bool:
		for s in utils.known_slugs():
			if s == slug:
				return False
		return True

	def match_by_valid(self, slug: str) -> bool:
		matches = re.findall(VALIDDATES, slug)
		return bool(matches and utils.valid_dates(matches[0][1], self.runtime) != [])

	def __init__(self, rootPath: Optional[str] = None, flag: Optional[str] = None) -> None:
		assert rootPath is not None or flag, "rootPath 和 flag 必须提供一个"
		match rootPath, flag:
			case _, fl if fl is not None:
				self.urlPath = Regions[fl].url_retail
			case rp, _ if rp is not None:
				self.urlPath = rp.replace("/cn", ".cn")
		self.using = self.match_by_valid if not utils.known_slugs() else self.match_by_assure
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

	async def getObjects(self, session: Optional[SessionType] = None) -> list[Collection | Course | Schedule]:
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as session:
			results = await AsyncGather((getURL(u, session = session, semaphore = semaphore)
				for u in await self.getURLs()), return_exceptions = True)
		return [i for i in results if not isinstance(i, BaseException)]

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

lang = {
	True: {
		"OR": "或",
		"NEW": "新",
		"JOINT": "、",
		"COURSE": "课程",
		"COLLECTION": "系列",
		"STORES": "家",
		"VIRTUAL": "线上活动",
		"COLLAB_WITH": "*合作机构*",
		"DOWNLOAD_IMAGE": "下载图片",
		"LEARN_COLLECTION": "了解系列",
		"LEARN_COURSE": "了解课程",
		"INTRO_COLLECTION": "*系列简介*",
		"INTRO_COURSE": "*课程简介*",
		"SIGN_UP": "预约课程",
		"GENERAL_STORE": "Apple Store 零售店",
		"IN_COLLECTION": "{NAME} 系列课程\n",
		"START_FROM": "{START} – {END}{TZTEXT}",
		"START_FROM_ALL": "{START} – {END}{TZTEXT} 起",
		"GENERAL_TIMING": "尚无可确定的课程时间",
		"SIGN_UP_ALL": "所有场次均可预约",
		"SIGN_UP_NONE": "所有场次均不可预约",
		"SIGN_UP_SOME": "✅ {AALL} 场中的 {AOK} 场可预约",
		"SIGN_UP_SINGLE": "✅ 本场活动可预约",
		"SIGN_UP_NOT": "❌ 本场活动不可预约",
		"SIGN_UP_STATUS": "*可预约状态*",
		"FORMAT_START": "%-m 月 %-d 日 %-H:%M",
		"FORMAT_END": "%-H:%M",
		"FORMAT_DATE": "%Y 年 %-m 月 %-d 日",
		"MAIN1": "#TodayatApple {NEW}{TYPE}\n\n*{NAME}*\n\n{INTROTITLE}\n{INTRO}",
		"MAIN2": "#TodayatApple {NEW}{TYPE}\n\n{PREFIX}*{NAME}*\n\n🗺️ {LOCATION}\n🕘 {TIME}\n\n{INTROTITLE}\n{INTRO}\n\n{SIGNPREFIX}\n{SIGN}"},
	False: {
		"OR": "/",
		"NEW": "",
		"JOINT": ", ",
		"COURSE": "Course",
		"COLLECTION": "Collection",
		"STORES": "Store{PLURAL}",
		"VIRTUAL": "Virtual Event",
		"COLLAB_WITH": "*In collaboration with*",
		"LEARN_COLLECTION": "Learn More",
		"DOWNLOAD_IMAGE": "Poster",
		"LEARN_COURSE": "Learn More",
		"INTRO_COLLECTION": "*Description*",
		"INTRO_COURSE": "*Description*",
		"SIGN_UP": "Sign Up",
		"GENERAL_STORE": "Apple Retail Store",
		"IN_COLLECTION": "In Collection {NAME}\n",
		"START_FROM": "{START} – {END}{TZTEXT}",
		"START_FROM_ALL": "Starting {START} – {END}{TZTEXT}",
		"GENERAL_TIMING": "Indeterminable Time",
		"SIGN_UP_ALL": "All available for sign up",
		"SIGN_UP_NONE": "Not available for sign up",
		"SIGN_UP_SOME": "✅ {AOK} of {AALL} available for sign up",
		"SIGN_UP_SINGLE": "✅ Available for sign up",
		"SIGN_UP_NOT": "❌ Not available for sign up",
		"SIGN_UP_STATUS": "*Sign Up status*",
		"FORMAT_START": "%b %-d, %-H:%M",
		"FORMAT_END": "%-H:%M",
		"FORMAT_DATE": "%Y/%-m/%-d",
		"MAIN1": "#TodayatApple {NEW}{TYPE}\n\n*{NAME}*\n\n{INTROTITLE}\n{INTRO}",
		"MAIN2": "#TodayatApple {NEW}{TYPE}\n\n{PREFIX}*{NAME}*\n\n🗺️ {LOCATION}\n🕘 {TIME}\n\n{INTROTITLE}\n{INTRO}\n\n{SIGNPREFIX}\n{SIGN}"}}

def teleinfo(
	course: Optional[Course] = None,
	schedules: list[Schedule] = [],
	collection: Optional[Collection] = None,
	mode: str = "new",
	userLang: bool = True,
	prior: Sequence[str] = []) -> tuple[str, str, list[list[list[str]]]]:

	runtime = datetime.now()
	offset = (runtime.astimezone().utcoffset() or timedelta()).total_seconds() / 3600
	priorlist = (*prior, *Regions)

	if collection is not None:
		text = disMarkdown(lang[userLang]["MAIN1"].format(
			NEW = lang[userLang]["NEW"] if mode == "new" else '',
			TYPE = lang[userLang]["COLLECTION"],
			NAME = collection.name,
			INTROTITLE = lang[userLang]["INTRO_COLLECTION"],
			INTRO = collection.description['long']))
		if collection.talents != []:
			collab = []
			for c in collection.talents:
				name = disMarkdown(c.name)
				collab.append(f"[{name}]({c.links['URL']})" if "URL" in c.links else name)
			text += f"\n\n{lang[userLang]['COLLAB_WITH']}\n{lang[userLang]['JOINT'].join(collab)}"

		image = collection.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"
		keyboard = [[[lang[userLang]["LEARN_COLLECTION"], collection.url], [lang[userLang]["DOWNLOAD_IMAGE"], collection.images["landscape"]]]]

		return text, image, keyboard

	assert course is not None
	schedules = sorted(set(schedules))

	if course.virtual:
		courseStore = lang[userLang]["VIRTUAL"]
	elif schedules == []:
		courseStore = lang[userLang]["GENERAL_STORE"]
	elif len(schedules) == 1:
		courseStore = str(schedules[0].raw_store)
	else:
		storeCounts = {r: len([s for s in {i.raw_store for i in schedules} if s.flag == r]) for r in priorlist}
		textStore = [f"{k} ({v} {lang[userLang]['STORES'].format(PLURAL = 's' if v > 1 else '')})"
			for k, v in storeCounts.items() if v]
		courseStore = lang[userLang]["JOINT"].join(textStore)

	if course.collection is None:
		specialPrefix = ""
	elif isinstance(course.collection, Collection):
		specialPrefix = lang[userLang]["IN_COLLECTION"].format(NAME = course.collection.name)
	else:
		specialPrefix = lang[userLang]["IN_COLLECTION"].format(NAME = course.collection)

	if schedules != []:
		priorSchedule = schedules[0] if prior == [] else sorted(
			schedules, key = lambda k: priorlist.index(k.flag))[0]

		tzText = ""
		if isinstance(priorSchedule.timeStart, datetime):
			if (priorSchedule.timeStart.utcoffset() or timedelta()).total_seconds() / 3600 != offset:
				tzText = " " + tz_text(priorSchedule.timeStart)

		timing = lang[userLang]["START_FROM" if len(schedules) == 1 else "START_FROM_ALL"].format(
			START = priorSchedule.datetimeStart(form = lang[userLang]["FORMAT_START"]),
			END = priorSchedule.datetimeEnd(form = lang[userLang]["FORMAT_END"]), TZTEXT = tzText)
		keyboard = [[[lang[userLang]["SIGN_UP"], priorSchedule.url]]]
	else:
		try:
			date = re.findall(VALIDDATES, course.slug)[0][1]
			vals = utils.valid_dates(date, runtime)
			timing = f' {lang[userLang]["OR"]} '.join(i.strftime(lang[userLang]["FORMAT_DATE"]) for i in vals)
		except IndexError:
			timing = lang[userLang]["GENERAL_TIMING"]
		keyboard = [[[lang[userLang]["LEARN_COURSE"], course.url]]]

	keyboard[0].append([lang[userLang]["DOWNLOAD_IMAGE"], course.images["landscape"]])

	if mode == "new" or schedules == []:
		signing = signingPrefix = ""
	else:
		upCount = len([s for s in schedules if s.status])
		seCount = len(schedules)
		if seCount > 1:
			if upCount:
				if upCount == seCount:
					signing = lang[userLang]["SIGN_UP_ALL"]
				else:
					signing = lang[userLang]["SIGN_UP_SOME"].format(AOK = upCount, AALL = seCount)
			else:
				signing = lang[userLang]["SIGN_UP_NONE"]
		elif upCount:
			signing = lang[userLang]["SIGN_UP_SINGLE"]
		else:
			signing = lang[userLang]["SIGN_UP_NOT"]
		signingPrefix = lang[userLang]["SIGN_UP_STATUS"]

	text = disMarkdown(lang[userLang]["MAIN2"].format(
		NEW = lang[userLang]["NEW"] if mode == "new" else '',
		TYPE = lang[userLang]["COURSE"],
		PREFIX = specialPrefix,
		NAME = course.name,
		LOCATION = courseStore,
		TIME = timing,
		INTROTITLE = lang[userLang]["INTRO_COURSE"],
		INTRO = course.description["long"],
		SIGNPREFIX = signingPrefix,
		SIGN = signing)).strip("\n")

	image = course.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"

	return text, image, keyboard