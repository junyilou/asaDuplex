import aiohttp
import asyncio
import itertools
import json
import re

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from modules.constants import allRegions, userAgent
from modules.util import SessionType, disMarkdown, request, timezoneText
from storeInfo import Store as Raw_Store, getStore as getRaw_Store, sidify, storeReturn
from typing import Any, AsyncIterator, Literal, Optional, Self
from zoneinfo import ZoneInfo

__SAVED = {"Store": {}, "Course": {}, "Schedule": {}, "Collection": {}}
ACCEPT = ["jpg", "png", "mp4", "mov", "pages", "key", "pdf"]
PARAM = {"ensureAns": False, "timeout": 25, "retryNum": 5}
SEMAPHORE_LIMIT = 20
VALIDDATES = r"(-([0-9]{4,8}))$"

todayNation: dict[str, Any] = {allRegions[i]["rootPath"]: i for i in allRegions}

@asynccontextmanager
async def get_session() -> AsyncIterator[SessionType]:
	session = aiohttp.ClientSession(headers = userAgent)
	try:
		yield session
	finally:
		await session.close()

class APIClass:
	args = {
		"COLLECTIONSLUG": "collectionSlug",
		"COURSESLUG": "courseSlug",
		"ROOTPATH": "stageRootPath",
		"SCHEDULEID": "scheduleId",
		"STORESLUG": "storeSlug"}

	def __init__(self, parts: list[str]) -> None:
		self._parts: list[str] = parts

	def __getitem__(self, key: str) -> Self:
		return APIClass(parts = self._parts + [key])

	def __repr__(self) -> str:
		return "/".join(self._parts)

	def format(self, **kwargs) -> str:
		return "/".join(self._parts) + "?" + "&".join(f"{self.args.get(k, k)}={v}" for k, v in kwargs.items())

API = APIClass("https://www.apple.com/today-bff".split("/"))

class utils:
	@staticmethod
	def known_slugs() -> list[str]:
		try:
			with open("Retail/savedEvent.json") as r:
				assure = json.loads(r.read())
			return [assure["today"][i]["slug"] for i in assure["assure"]]
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
		raw: Optional[dict] = None,
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
			self.rootPath: str = rootPath or self.raw_store.region["rootPath"]
			self.flag: str = todayNation[self.rootPath]
			self.url: str = f"https://www.apple.com{raw['path']}" if self.rootPath != "/cn" \
				else f"https://www.apple.com.cn{raw['path']}"
			self.coord: Optional[list[float]] = [raw["lat"], raw["long"]]
		else:
			temp = store or (getRaw_Store(sid) if sid else None)
			assert temp is not None, f"本地数据库中无法匹配关键字 {sid!r}"
			self.raw_store: Raw_Store = temp
			self.sid: str = self.raw_store.rid
			self.name: str = self.raw_store.name
			self.slug: str = self.raw_store.slug
			self.rootPath: str = rootPath or self.raw_store.region["rootPath"]
			self.timezone: str = self.raw_store.timezone
			self.flag: str = todayNation[self.rootPath]
			self.url: str = self.raw_store.url
			self.coord: Optional[list[float]] = None
		self.today: str = self.url.replace("/retail/", "/today/")
		self.calendar: str = self.url.replace("/retail/", "/today/calendar/")
		self.serial: dict[str, str] = {"sid": self.sid}
		self.raw: dict[str, Any] = {k: v for k, v in vars(self).items() if k != "raw"}

	def __repr__(self) -> str:
		return f'<Store "{self.name}" ({self.sid}), "{self.slug}", "{self.rootPath}">'

	async def getCourses(self, ensure: bool = True) -> list["Course"]:
		async with get_session() as session:
			nearby = {"nearby": "true"} if not ensure else {}
			r = await request(session = session, url = (API["landing"]["store" if ensure else "nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath, **nearby), **PARAM)
		try:
			remote = json.loads(utils.separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			for c in remote["courses"].values():
				tasks.append(tg.create_task(getCourse(remote = remote, rootPath = self.rootPath, slug = c["urlTitle"])))
		return [t.result() for t in tasks]

	async def getSchedules(self, ensure: bool = True) -> list["Schedule"]:
		async with get_session() as session:
			nearby = {"nearby": "true"} if not ensure else {}
			r = await request(session = session, url = (API["landing"]["store" if ensure else "nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath, **nearby), **PARAM)
		try:
			remote = json.loads(utils.separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			for i, s in remote["schedules"].items():
				storeNum = s["storeNum"]
				course = remote["courses"][s["courseId"]]
				if not ensure or storeNum == self.sid or "VIRTUAL" in course["type"]:
					if s["courseId"] not in remote["courses"]:
						continue
					tasks.append(tg.create_task(getSchedule(
						scheduleId = i, remote = remote, rootPath = self.rootPath,
						slug = course["urlTitle"])))
		return [t.result() for t in tasks]

	async def getCoord(self) -> list[float]:
		async with get_session() as session:
			d = await self.raw_store.detail(session = session, mode = "raw")
		assert isinstance(d, dict)
		self.coord = [i[1] for i in sorted(d["geolocation"].items())]
		return self.coord

def getStore(
	sid: int | str,
	raw: Optional[dict] = None,
	rootPath: Optional[str] = None,
	store: Optional[Raw_Store] = None) -> Store:

	global __SAVED
	sid = sidify(sid, R = True)
	if sid in __SAVED["Store"] and raw is not None:
		get = Store(raw = raw, rootPath = rootPath)
	else:
		get = Store(sid = sid, store = store, raw = raw, rootPath = rootPath)
	__SAVED["Store"][sid] = get
	return get

class Talent(TodayObject):
	hashattr: list[str] = ["name"]
	sortkeys: list[str] = ["name"]

	def __init__(self, raw: dict[str, Any]) -> None:
		self.raw: dict[str, Any] = raw
		self.name: str = raw["name"].strip()
		self.title: Optional[str] = raw["title"].strip() if "title" in raw else None
		self.description: Optional[str] = raw["description"].strip() if "description" in raw else None
		self.image: Optional[str] = raw.get("backgroundImage", None) or raw.get("logo", None)
		self.links: dict[str, str] = (
			({"Website": raw["websiteUrl"]} if "websiteUrl" in raw else {}) |
			({"URL": raw["url"]} if "url" in raw else {}) |
			({social["name"].capitalize(): social["url"] for social in raw.get("socialLinks", {})}))

	def __repr__(self) -> str:
		return f'<Talent "{self.name}"' + (f', "{self.title}"' if self.title else "") + ">"

class Course(TodayObject):
	hashattr: list[str] = ["rootPath", "slug"]
	sortkeys: list[str] = ["courseId", "rootPath"]

	@classmethod
	async def get(cls,
		rootPath: str,
		slug: str,
		remote: Optional[dict] = None) -> Self:
		if remote is None:
			async with get_session() as session:
				r = await request(session = session, url = API["session"]["course"].format(
					COURSESLUG = slug, ROOTPATH = rootPath), **PARAM)
			try:
				remote = json.loads(utils.separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课程 {rootPath}/{slug} 数据失败") from None

		assert isinstance(remote, dict), f"课程 {rootPath}/{slug} 数据信息无效"
		courseId: str = next(t[0] for t in remote["courses"].items() if t[1]["urlTitle"] == slug)
		talents: list[dict] = remote.get("talents", [])
		raw: dict[str, Any] = remote["courses"][courseId]
		moreAbout, collection = [], raw.get("collectionName")
		if "moreAbout" in remote:
			moreAbout.append(remote["moreAbout"])
		if "heroGallery" in remote:
			for m in remote["heroGallery"]:
				if m.get("heroType", None) == "TAG":
					moreAbout.append(m)
		for more in moreAbout:
			if collection and any(collection == more.get(k, k) for k in ["title", "name"]):
				collection = await getCollection(rootPath = rootPath, slug = more["collId"])

		return cls(courseId = courseId, raw = raw, rootPath = rootPath, collection = collection, talents = talents)

	def __init__(self,
		courseId: str,
		raw: dict[str, Any],
		rootPath: str,
		collection: Optional["str | Collection"] = None,
		talents: list[dict] = []) -> None:

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
		semaphore: Optional[asyncio.Semaphore] = None) -> list["Schedule"]:
		if semaphore is not None:
			await semaphore.acquire()
		async with get_session() as session:
			r = await request(session = session, url = (API["session"]["course"]["store" if ensure else "nearby"]).format(
				STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath), **PARAM)
		if semaphore is not None:
			semaphore.release()
		try:
			remote = json.loads(utils.separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取排课 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			schedules = remote["schedules"]
			for i in remote["schedules"]:
				storeNum = schedules[i]["storeNum"]
				if schedules[i]["courseId"] == self.courseId:
					if not ensure or storeNum == store.sid or "VIRTUAL" in remote["courses"][self.courseId]["type"]:
						tasks.append(tg.create_task(getSchedule(
							scheduleId = i, remote = remote, rootPath = store.rootPath, slug = self.slug)))
		return [t.result() for t in tasks]

	async def getRootSchedules(self, rootPath: Optional[str] = None) -> list["Schedule"]:
		rootPath = rootPath or self.rootPath
		stores = storeReturn(todayNation[rootPath], remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		tasks = (self.getSchedules(getStore(sid = i.sid, store = i, rootPath = rootPath), semaphore = semaphore) for i in stores)
		results = await asyncio.gather(*tasks, return_exceptions = True)
		return sorted(set(itertools.chain.from_iterable(results)))

async def getCourse(
	courseId: Optional[int | str] = None,
	fuzzy: bool = True,
	remote: Optional[dict] = None,
	rootPath: Optional[str] = None,
	slug: Optional[str] = None) -> Course:

	global __SAVED
	courseId = str(courseId)

	if remote is not None:
		assert rootPath is not None and slug is not None, "在提供字典模式下 rootPath 和 slug 必须提供"
		obj = await Course.get(slug = slug, rootPath = rootPath, remote = remote)
		__SAVED["Course"][f"{obj.rootPath}/{obj.courseId}"] = obj
		return obj

	keyword = courseId
	if not fuzzy:
		assert rootPath is not None, "在非模糊模式下 rootPath 必须提供"
		keyword = "/".join([rootPath, keyword])
	for i, c in __SAVED["Course"].items():
		if (fuzzy and keyword in i) or (not fuzzy and keyword == i):
			return c

	assert slug is not None and rootPath is not None, "没有找到匹配时 slug 和 rootPath 必须全部提供"
	obj = await Course.get(slug = slug, rootPath = rootPath)
	__SAVED["Course"][f"{obj.rootPath}/{obj.courseId}"] = obj
	return obj

class Schedule(TodayObject):
	hashattr: list[str] = ["rootPath", "scheduleId", "slug"]
	sortkeys: list[str] = ["rawStart", "scheduleId"]

	@classmethod
	async def get(cls,
		rootPath: str,
		scheduleId: str,
		slug: str,
		remote: Optional[dict] = None) -> Self:
		if remote is None:
			scheduleId = f"{scheduleId}"
			async with get_session() as session:
				r = await request(session = session, url = API["session"]["schedule"].format(
					COURSESLUG = slug, SCHEDULEID = scheduleId, ROOTPATH = rootPath), **PARAM)
			try:
				remote = json.loads(utils.separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取排课 {rootPath}/{slug}/{scheduleId} 数据失败") from None

		assert isinstance(remote, dict), f"排课 {rootPath}/{slug}/{scheduleId} 数据信息无效"
		store: Store = getStore(
			sid = remote["schedules"][scheduleId]["storeNum"],
			raw = remote["stores"].get(remote["schedules"][scheduleId]["storeNum"], None),
			rootPath = rootPath)
		course: Course = await getCourse(
			remote = remote, rootPath = rootPath,
			slug = remote["courses"][remote["schedules"][scheduleId]["courseId"]]["urlTitle"])
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
		if isinstance(self.timeStart, datetime):
			return self.timeStart.astimezone(self.tzinfo).strftime(form)
		return self.rawStart.strftime(form)

	def datetimeEnd(self, form: str = "%-H:%M") -> str:
		if isinstance(self.timeEnd, datetime):
			return self.timeEnd.astimezone(self.tzinfo).strftime(form)
		return self.rawEnd.strftime(form)

	def __repr__(self) -> str:
		loc = self.store.sid if not self.course.virtual else "Online"
		return f'<Schedule {self.scheduleId} of {self.course.courseId}, {self.datetimeStart("%-m/%-d %-H:%M")}-{self.datetimeEnd()} @ {loc}>'

async def getSchedule(
	scheduleId: int | str,
	remote: Optional[dict] = None,
	rootPath: Optional[str] = None,
	slug: Optional[str] = None) -> Schedule:

	global __SAVED
	scheduleId = str(scheduleId)

	if remote is not None:
		assert rootPath is not None and slug is not None, "在提供字典模式下 rootPath 和 slug 必须提供"
		obj = await Schedule.get(rootPath = rootPath, scheduleId = scheduleId, slug = slug, remote = remote)
		__SAVED["Schedule"][obj.scheduleId] = obj
		return obj

	if scheduleId in __SAVED["Schedule"]:
		return __SAVED["Schedule"][scheduleId]

	assert slug is not None and rootPath is not None, "没有找到匹配时 slug 和 rootPath 必须全部提供"
	obj = await Schedule.get(rootPath = rootPath, scheduleId = scheduleId, slug = slug)
	__SAVED["Schedule"][obj.scheduleId] = obj
	return obj

class Collection(TodayObject):
	hashattr: list[str] = ["rootPath", "slug"]
	sortkeys: list[str] = ["rootPath", "slug"]

	@classmethod
	async def get(cls,
		rootPath: str,
		slug: str,
		remote: Optional[dict] = None) -> Self:
		if remote is None:
			async with get_session() as session:
				r = await request(session = session, url = API["collection"]["geo"].format(
					COLLECTIONSLUG = slug, ROOTPATH = rootPath), **PARAM)
			try:
				remote = json.loads(utils.separate(r))
			except json.decoder.JSONDecodeError:
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

		self.collaborations: list[Talent]
		if "inCollaborationWith" in raw:
			self.collaborations = [Talent(raw = t) for t in raw["inCollaborationWith"]["partners"]]
		else:
			self.collaborations = []
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
		semaphore: Optional[asyncio.Semaphore] = None) -> list[Schedule]:
		if semaphore is not None:
			await semaphore.acquire()
		async with get_session() as session:
			r = await request(session = session, url = (API["collection"]["store" if ensure else "nearby"]).format(
				STORESLUG = store.slug, COLLECTIONSLUG = self.slug, ROOTPATH = store.rootPath), **PARAM)
		if semaphore is not None:
			semaphore.release()
		try:
			remote = json.loads(utils.separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取排课 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			for i, s in remote["schedules"].items():
				courseId = s["courseId"]
				storeNum = s["storeNum"]
				course = remote["courses"][courseId]
				if self.slug in (m["collId"] for m in remote["heroGallery"] if m["heroType"] == "TAG"):
					if not ensure or storeNum == store.sid or "VIRTUAL" in course["type"]:
						tasks.append(tg.create_task(getSchedule(
							scheduleId = i, remote = remote, rootPath = store.rootPath, slug = course["urlTitle"])))
		return [t.result() for t in tasks]

	async def getRootSchedules(self, rootPath: Optional[str] = None) -> list[Schedule]:
		rootPath = rootPath or self.rootPath
		stores = storeReturn(todayNation[rootPath], remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		tasks = (self.getSchedules(getStore(sid = i.sid, store = i, rootPath = rootPath), semaphore = semaphore) for i in stores)
		results = await asyncio.gather(*tasks, return_exceptions = True)
		return sorted(set(itertools.chain.from_iterable(results)))

	async def getCourses(self, rootPath: Optional[str] = None) -> list[Course]:
		schedules = await self.getRootSchedules(rootPath = rootPath)
		return sorted(set((schedule.course for schedule in schedules)))

async def getCollection(
	rootPath: str,
	slug: str) -> Collection:

	global __SAVED
	keyword = f"{rootPath}/{slug}"
	for i, c in __SAVED["Collection"].items():
		if keyword == i:
			return c

	obj = await Collection.get(rootPath = rootPath, slug = slug)
	__SAVED["Collection"][keyword] = obj
	return obj

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
				self.urlPath = allRegions[fl]["storeURL"]
			case rp, _ if rp is not None:
				self.urlPath = rp.replace("/cn", ".cn")
		self.using = self.match_by_valid if not utils.known_slugs() else self.match_by_assure
		self.runtime = datetime.now()
		self.raw = {"urlPath": self.urlPath}

	def __repr__(self) -> str:
		return f'<Sitemap "{self.urlPath}">'

	async def getURLs(self) -> list[str]:
		async with get_session() as session:
			r = await request(session = session, url = f"https://www.apple.com{self.urlPath}/today/sitemap.xml", **PARAM)
		urls = re.findall(r"<loc>\s*(\S*)\s*</loc>", r)

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

	async def getObjects(self) -> list[Course | Schedule]:
		return await asyncio.gather(*(getURL(u) for u in await self.getURLs()), return_exceptions = True)

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

async def getURL(url: str) -> TodayObject:
	match parseURL(url):
		case {"type": "schedule", "rootPath": r, "slug": g, "scheduleId": s}:
			return await getSchedule(scheduleId = s, rootPath = r, slug = g)
		case {"type": "course", "rootPath": r, "slug": g}:
			return await getCourse(fuzzy = False, rootPath = r, slug = g)
		case {"type": "collection", "rootPath": r, "slug": g}:
			return await getCollection(rootPath = r, slug = g)
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
	prior: list[str] = []) -> tuple[str, str, list[list[list[str]]]]:

	runtime = datetime.now()
	offset = (runtime.astimezone().utcoffset() or timedelta()).total_seconds() / 3600
	priorlist = prior + list(allRegions)

	if collection is not None:
		text = disMarkdown(lang[userLang]["MAIN1"].format(
			NEW = lang[userLang]["NEW"] if mode == "new" else '',
			TYPE = lang[userLang]["COLLECTION"],
			NAME = collection.name,
			INTROTITLE = lang[userLang]["INTRO_COLLECTION"],
			INTRO = collection.description['long']))
		if collection.collaborations != []:
			collab = []
			for c in collection.collaborations:
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
		courseStore = schedules[0].raw_store.telename(sid = False)
	else:
		storeSets = set([i.raw_store for i in schedules])
		storeCounts = {r: len([s for s in storeSets if s.flag == r]) for r in priorlist}
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
				tzText = " " + timezoneText(priorSchedule.timeStart)

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