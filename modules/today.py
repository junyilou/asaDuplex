import aiohttp
import asyncio
import atexit
import json
import re

from datetime import datetime
from modules.constants import allRegions, userAgent
from modules.util import disMarkdown, request, timezoneText
from storeInfo import StoreID, nameReplace, storeReturn
from storeInfo import Store as Raw_Store
from typing import Any, Optional
from zoneinfo import ZoneInfo

__session_pool = {}
savedToday = {"Store": {}, "Course": {}, "Schedule": {}, "Collection": {}}
todayNation: dict[str, Any] = {allRegions[i]["rootPath"]: i for i in allRegions}

_RETRYNUM = 5
_SEMAPHORE_LIMIT = 25
_TIMEOUT = 5

_ACCEPT = ["jpg", "png", "mp4", "mov", "pages", "key", "pdf"]
_ASSURED_JSON = "Retail/savedEvent.json"
_VALIDDATES = r"(-([0-9]{6,8}))"

API_ROOT = "https://www.apple.com/today-bff/"
API = {
	"landing": {
		"store": API_ROOT + "landing/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}",
		"nearby": API_ROOT + "landing/nearby?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&nearby=true",
	},
	"session": {
		"course": API_ROOT + "session/course?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}",
		"schedule": API_ROOT + "session/schedule?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}&scheduleId={SCHEDULEID}",
		"store": API_ROOT + "session/course/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&courseSlug={COURSESLUG}",
		"nearby": API_ROOT + "session/course/nearby?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&courseSlug={COURSESLUG}",
	},
	"collection": {
		"geo": API_ROOT + "collection/geo?stageRootPath={ROOTPATH}&collectionSlug={COLLECTIONSLUG}",
		"store": API_ROOT + "collection/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&collectionSlug={COLLECTIONSLUG}",
		"nearby": API_ROOT + "collection/nearby?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&collectionSlug={COLLECTIONSLUG}",
	}
}

try:
	with open(_ASSURED_JSON) as r:
		assure = json.loads(r.read())
	knownSlugs = [assure["today"][i]["slug"] for i in assure["assure"]]
except FileNotFoundError:
	knownSlugs = []

@atexit.register
def clean(loop = None):
	try:
		l = [asyncio.get_running_loop()] if loop is None else [loop]
	except:
		l = [i for i in __session_pool]

	async def __clean_task(loop):
		await __session_pool[loop].close()
		del __session_pool[loop]

	for loop in l:
		if loop.is_closed():
			return
		if not loop.is_running():
			loop.run_until_complete(__clean_task(loop))
		else:
			loop.create_task(__clean_task(loop))

def _get_session():
	loop = asyncio.get_running_loop()
	session = __session_pool.get(loop, None)
	if session is None:
		session = aiohttp.ClientSession(loop = loop, headers = userAgent)
		__session_pool[loop] = session
	return session

def _resolution(vids: list[str], direction: Optional[str] = None) -> list[str]:
	res = {}
	for v in vids:
		f = re.findall(r"([0-9]+)x([0-9]+)\.[a-zA-Z0-9]+", v)
		if not f:
			return vids
		res[v] = [int(f[0][0]), int(f[0][1])]
	vids.sort(key = lambda k: res[k][0] * res[k][1], reverse = True)

	if not direction:
		return vids
	else:
		match direction:
			case "p":
				fil = [i for i in vids if res[i][0] < res[i][1]]
			case "l":
				fil = [i for i in vids if res[i][0] > res[i][1]]
			case _:
				fil = []
		return fil

def _separate(text: str) -> str:
	rep = {0xa0: 0x20, 0x200b: None, 0x200c: None, 0x2060: None}
	return text.translate(rep)

def _validDates(ex: str, runtime: datetime) -> list[datetime]:
	v = []
	match len(ex):
		case 6:
			possible = ["%y%m%d", "%d%m%y", "%m%d%y"]
		case 8:
			possible = ["%Y%m%d", "%d%m%Y", "%m%d%Y"]
		case _:
			possible = []
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

class asyncObject(object):
	async def __new__(cls, *args, **kwargs):
		instance = super().__new__(cls)
		await instance.__init__(*args, **kwargs)
		return instance

	async def __init__(self):
		pass

class TodayEncoder(json.JSONEncoder):
	def __init__(self, **kwargs):
		super().__init__(**(kwargs | {"ensure_ascii": False}))

	def default(self, o):
		match o:
			case Store() | Raw_Store() | Course() | Schedule() | Collection() | Talent():
				return o.raw
			case _:
				return super().default(o)

class Store():
	def __init__(self, sid: Optional[int | str] = None, raw: Optional[dict] = None,
		store: Optional[Raw_Store] = None, rootPath: Optional[str] = None):

		assert raw or sid or store, "raw, sid, store 至少提供一个"
		if raw:
			self.name: str = raw["name"]
			self.sid: str = raw["storeNum"]
			self.raw_store: Raw_Store = StoreID(self.sid)[0]
			self.timezone: str = raw["timezone"]["name"]
			self.slug: str = raw["slug"]
			self.rootPath: str = rootPath or self.raw_store.region["rootPath"]
			self.flag: str = todayNation[self.rootPath]
			self.url: str = f"https://www.apple.com{raw['path']}" if self.rootPath != "/cn" \
				else f"https://www.apple.com.cn{raw['path']}"
			self.coord: list[float] = [raw["lat"], raw["long"]]
		elif sid or store:
			self.raw_store: Raw_Store = store or StoreID(sid)[0]
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
		self.serial: dict[str, str] = dict(sid = self.sid)
		self.raw: dict = {k: v for k, v in vars(self).items() if k != "raw"}

	def __repr__(self):
		return f'<Store "{self.name}" ({self.sid}), "{self.slug}", "{self.rootPath}">'

	def __hash__(self):
		return hash(self.serial)

	def __lt__(self, other):
		return type(other) is type(self) and self.raw_store.sortkey < other.raw_store.sortkey

	def __gt__(self, other):
		return type(other) is type(self) and self.raw_store.sortkey > other.raw_store.sortkey

	def __eq__(self, other):
		return type(other) is type(self) and self.raw_store.sortkey == other.raw_store.sortkey

	async def getCourses(self, ensure: bool = True) -> list["Course"]:

		r = await request(
			session = _get_session(),
			url = (API["landing"]["store"] if ensure else API["landing"]["nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)

		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			for i in raw["courses"]:
				tasks.append(tg.create_task(getCourse(
					courseId = i, raw = raw["courses"][i], rootPath = self.rootPath,
					moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
					stores = raw["stores"], fuzzy = False)))
		return [t.result() for t in tasks]

	async def getSchedules(self, ensure: bool = True) -> list["Schedule"]:

		r = await request(
			session = _get_session(),
			url = (API["landing"]["store"] if ensure else API["landing"]["nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)

		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			schedules = raw["schedules"]
			for i in raw["schedules"]:
				storeNum = schedules[i]["storeNum"]
				if (not ensure) or (storeNum == self.sid) or \
				("VIRTUAL" in raw["courses"][raw["schedules"][i]["courseId"]]["type"]):
					if schedules[i]["courseId"] not in raw["courses"]:
						continue
					tasks.append(tg.create_task(getSchedule(
						scheduleId = i, raw = schedules[i],
						rootPath = self.rootPath, slug = self.slug,
						store = getStore(
							sid = storeNum, rootPath = self.rootPath,
							raw = raw["stores"][storeNum] if storeNum in raw["stores"] else None),
						course = await getCourse(
							courseId = schedules[i]["courseId"],
							raw = raw["courses"][schedules[i]["courseId"]],
							rootPath = self.rootPath,
							moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
							fuzzy = False))))
		return [t.result() for t in tasks]

	async def getCoord(self) -> list[float]:
		d = await self.raw_store.detail(session = _get_session(), mode = "raw")
		self.coord = [i[1] for i in sorted(d["geolocation"].items())]
		return self.coord

def getStore(sid: int | str, raw: Optional[dict] = None, store: Optional[Raw_Store] = None, rootPath: Optional[str] = None) -> Store:
	global savedToday
	sid = f"R{str(sid).removeprefix('R'):0>3}"
	if sid in savedToday["Store"] and raw is not None:
		get = Store(raw = raw, rootPath = rootPath)
		savedToday["Store"][sid] = get
	else:
		get = Store(sid = sid, store = store, raw = raw, rootPath = rootPath)
		savedToday["Store"][sid] = get
	return savedToday["Store"][sid]

class Talent():
	def __init__(self, raw: dict):
		self.raw: dict = raw
		self.name: str = raw["name"].strip()
		self.title: Optional[str] = raw["title"].strip() if "title" in raw else None
		self.description: str = raw["description"].strip()
		self.image: str = raw.get("backgroundImage", None) or raw.get("logo", None)
		self.links: dict[str, str] = ({"Website": raw["websiteUrl"]} if "websiteUrl" in raw else {} |
			{"URL": raw["url"]} if "url" in raw else {} |
			{social["name"].capitalize(): social["url"] for social in raw.get("socialLinks", {})})

	def __repr__(self):
		return f'<Talent "{self.name}"' + (f', "{self.title}"' if self.title else "") + ">"

class Course(asyncObject):
	async def __init__(self, courseId: Optional[str] = None, raw: Optional[dict] = None, rootPath: Optional[str] = None,
		slug: Optional[str] = None, moreAbout: Optional[list | dict] = None, talents: Optional[list[dict]] = None):

		if raw is None:
			assert slug and rootPath is not None, "slug, rootPath 必须全部提供"

			r = await request(
				session = _get_session(),
				url = API["session"]["course"].format(COURSESLUG = slug, ROOTPATH = rootPath),
				ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)

			try:
				raw = json.loads(_separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课程 {rootPath}/{slug} 数据失败") from None

			courseId = [i for i in raw["courses"] if raw["courses"][i]["urlTitle"] == slug][0]
			moreAbout = raw.get("moreAbout", None)
			talents = raw["talents"]
			raw = raw["courses"][courseId]

		assert courseId and raw and rootPath is not None

		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.courseId: str = courseId
		self.name: str = raw["name"].strip()
		self.title: str = raw["title"]
		self.slug: str = raw["urlTitle"]
		self.serial: dict[str, str] = dict(slug = self.slug, rootPath = self.rootPath)

		self.collection: str | Collection = raw["collectionName"]
		if moreAbout is not None:
			moreAbout = [moreAbout] if isinstance(moreAbout, dict) else moreAbout
			for moreDict in moreAbout:
				if raw["collectionName"] in [moreDict.get("title", "title"), moreDict.get("name", "name")]:
					self.collection = await getCollection(rootPath = self.rootPath, slug = moreDict["collId"])
					break

		self.description: dict[str, str] = {
			"long": raw["longDescription"].strip(),
			"medium": raw["mediumDescription"].strip(),
			"short": raw["shortDescription"].strip()
		}

		self.intro: dict[str, str | list[str]]
		if raw["modalVideo"]:
			self.intro = {
				"poster": raw["modalVideo"]["poster"]["source"],
				"video": _resolution(raw["modalVideo"]["sources"])
			}
		else:
			self.intro = {}

		media = raw["backgroundMedia"]
		self.images: dict[str, str] = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]
		}
		self.videos: dict[str, dict[str, str | list[str]]]
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"videos": _resolution(media["ambientVideo"]["sources"], "p")
				},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": _resolution(media["ambientVideo"]["sources"], "l")
				}
			}
		else:
			self.videos = {}

		self.virtual: bool = "VIRTUAL" in raw["type"]
		self.special: bool = "SPECIAL" in raw["type"] or "HIGH" in raw["talentType"]
		self.talents: list[Talent] = [Talent(raw = t) for t in talents] if talents else []
		self.url: str = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}"
		self.raw: dict = raw | {"serial": self.serial}

	def __repr__(self):
		col = (f', Collection <{self.collection.name}>' if isinstance(self.collection, Collection) \
			else f', Collection "{self.collection}"') if self.collection is not None else ""
		return f'<Course {self.courseId} "{self.name}", "{self.slug}"{col}>'

	def __hash__(self):
		return hash((self.rootPath, self.courseId))

	def __lt__(self, other):
		return type(other) is type(self) and (self.courseId, self.rootPath) < (other.courseId, other.rootPath)

	def __gt__(self, other):
		return type(other) is type(self) and (self.courseId, self.rootPath) > (other.courseId, other.rootPath)

	def __eq__(self, other):
		return type(other) is type(self) and (self.courseId, self.rootPath) == (other.courseId, other.rootPath)

	def elements(self, accept: Optional[list[str]] = None) -> list[str]:
		accept = accept or _ACCEPT
		result, pattern = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + pattern +
			"))+[\'\"]?", json.dumps(self, cls = TodayEncoder)) if i[0] not in result]
		return result

	async def getSchedules(self, store: Store, ensure: bool = True, semaphore: Optional[asyncio.Semaphore] = None) -> list["Schedule"]:

		if semaphore is not None:
			await semaphore.acquire()
		r = await request(
			session = _get_session(),
			url = (API["session"]["store"] if ensure else API["session"]["nearby"]).format(
				STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)
		if semaphore is not None:
			semaphore.release()

		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			schedules = raw["schedules"]
			for i in raw["schedules"]:
				storeNum = schedules[i]["storeNum"]
				if (schedules[i]["courseId"] == self.courseId) and \
				((not ensure) or (storeNum == store.sid) or ("VIRTUAL" in raw["courses"][self.courseId]["type"])):
					tasks.append(tg.create_task(getSchedule(
						scheduleId = i, raw = schedules[i],
						rootPath = store.rootPath, slug = self.slug,
						store = getStore(
							sid = storeNum, raw = raw["stores"][storeNum],
							rootPath = store.rootPath),
						course = await getCourse(
							courseId = self.courseId, raw = raw["courses"][self.courseId],
							rootPath = store.rootPath, moreAbout = raw.get("moreAbout", None),
							talents = raw["talents"], fuzzy = False))))
		return [t.result() for t in tasks]

	async def getRootSchedules(self, rootPath: Optional[str] = None) -> list[list["Schedule"]]:
		rootPath = rootPath or self.rootPath
		stores = storeReturn(todayNation[rootPath], remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(_SEMAPHORE_LIMIT)
		tasks = [self.getSchedules(getStore(sid = i.sid, store = i, rootPath = rootPath), semaphore = semaphore) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

async def getCourse(courseId: Optional[int | str] = None, raw: Optional[dict] = None, rootPath: Optional[str] = None, slug: Optional[str] = None,
	moreAbout: Optional[list | dict] = None, talents: Optional[list[dict]] = None, fuzzy: bool = True, stores: dict[str, dict] = {}) -> Course:
	global savedToday
	saved = list(savedToday["Course"])
	if rootPath == "":
		rootPath = "/us"
	if not fuzzy:
		assert rootPath is not None, "在非模糊模式下 rootPath 必须提供"
		keyword = f"{rootPath}/{courseId}"
	else:
		keyword = f"{courseId}"
	for i in saved:
		if keyword in i:
			return savedToday["Course"][i]
	assert rootPath is not None or courseId is not None, "没有找到匹配，需要提供 slug, rootPath"
	_ = [getStore(store, raw = raw) for store, raw in stores.items()]

	get = await Course(raw = raw, courseId = courseId, rootPath = rootPath.replace("/us", ""), slug = slug, moreAbout = moreAbout, talents = talents)
	savedToday["Course"][f"{rootPath}/{get.courseId}"] = get
	return get

class Schedule(asyncObject):
	async def __init__(self, scheduleId: Optional[str] = None, raw: Optional[dict] = None, rootPath: Optional[str] = None,
		slug: Optional[str] = None, store: Optional[Store] = None, course: Optional[Course] = None):

		if raw is None:
			assert slug and scheduleId and rootPath is not None, "slug, scheduleId, rootPath 必须全部提供"
			self.slug: str = slug
			scheduleId = f"{scheduleId}"

			r = await request(
				session = _get_session(),
				url = API["session"]["schedule"].format(COURSESLUG = self.slug, SCHEDULEID = scheduleId, ROOTPATH = rootPath),
				ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)

			try:
				raw = json.loads(_separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课次 {rootPath}/{self.slug}/{scheduleId} 数据失败") from None

			store = getStore(
				sid = raw["schedules"][scheduleId]["storeNum"],
				raw = raw["stores"][raw["schedules"][scheduleId]["storeNum"]],
				rootPath = rootPath)
			course = await getCourse(
				courseId = raw["schedules"][scheduleId]["courseId"],
				raw = raw["courses"][raw["schedules"][scheduleId]["courseId"]],
				rootPath = rootPath, moreAbout = raw.get("moreAbout", None),
				talents = raw["talents"], fuzzy = False)
			raw = raw["schedules"][scheduleId]

		assert scheduleId and raw and rootPath is not None and course and store

		_ = [setattr(self, key, getattr(course, key)) for key in vars(course)]
		self.course: Course = course
		self.scheduleId: str = scheduleId
		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.serial: dict[str, str] = dict(slug = self.slug, scheduleId = scheduleId, rootPath = self.rootPath)

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
		self.raw: dict = raw | {"serial": self.serial}

	def datetimeStart(self, form: str = "%-m 月 %-d 日 %-H:%M") -> str:
		if isinstance(self.timeStart, datetime):
			return self.timeStart.astimezone(self.tzinfo).strftime(form)
		return self.rawStart.strftime(form)

	def datetimeEnd(self, form: str = "%-H:%M") -> str:
		if isinstance(self.timeEnd, datetime):
			return self.timeEnd.astimezone(self.tzinfo).strftime(form)
		return self.rawEnd.strftime(form)

	def __repr__(self):
		loc = self.store.sid if not self.course.virtual else "Online"
		return f'<Schedule {self.scheduleId} of {self.course.courseId}, {self.datetimeStart("%-m/%-d %-H:%M")}-{self.datetimeEnd()} @ {loc}>'

	def __hash__(self):
		return hash(self.scheduleId)

	def __lt__(self, other):
		return type(other) is type(self) and (self.rawStart, self.scheduleId) < (other.rawStart, other.scheduleId)

	def __gt__(self, other):
		return type(other) is type(self) and (self.rawStart, self.scheduleId) > (other.rawStart, other.scheduleId)

	def __eq__(self, other):
		return type(other) is type(self) and (self.rawStart, self.scheduleId) == (other.rawStart, other.scheduleId)

async def getSchedule(scheduleId: int | str, raw: Optional[dict] = None, rootPath: Optional[str] = None,
	slug: Optional[str] = None, store: Optional[Store] = None, course: Optional[Course] = None) -> Schedule:
	global savedToday
	scheduleId = f"{scheduleId}"
	if any([raw, rootPath, slug]):
		get = await Schedule(scheduleId = scheduleId, raw = raw, rootPath = rootPath, slug = slug, store = store, course = course)
		savedToday["Schedule"][scheduleId] = get
	return savedToday["Schedule"][scheduleId]

class Collection(asyncObject):
	async def __init__(self, rootPath: Optional[str] = None, slug: Optional[str] = None):

		assert slug and rootPath is not None, "slug, rootPath 必须全部提供"

		self.slug: str = slug
		self.rootPath: str = rootPath
		self.flag: str = todayNation[self.rootPath]
		self.url: str = f"https://www.apple.com{rootPath.replace('/cn', '.cn')}/today/collection/{slug}/"
		self.serial: dict[str, str] = dict(slug = slug, rootPath = rootPath)

		r = await request(
			session = _get_session(),
			url = API["collection"]["geo"].format(COLLECTIONSLUG = slug, ROOTPATH = rootPath),
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)

		try:
			raw = json.loads(_separate(r))
			self.name: str = raw["name"].strip()
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取系列 {rootPath}/{slug} 数据失败") from None

		self.description: dict[str, str] = {
			"long": raw["longDescription"].strip(),
			"medium": raw["mediumDescription"].strip(),
			"short": raw["shortDescription"].strip()
		}

		media = raw["heroGallery"][0]["backgroundMedia"]
		self.images: dict[str, str] = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]
		}
		self.videos: dict[str, dict[str, str | list[str]]]
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"videos": _resolution(media["ambientVideo"]["sources"], "p")
				},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"videos": _resolution(media["ambientVideo"]["sources"], "l")
				}
			}
		else:
			self.videos = {}

		self.collaborations: list[Talent]
		if "inCollaborationWith" in raw:
			self.collaborations = [Talent(raw = t) for t in raw["inCollaborationWith"]["partners"]]
		else:
			self.collaborations = []
		self.raw: dict = raw | {"serial": self.serial}

	def __repr__(self):
		return f'<Collection "{self.name}", "{self.slug}", "{self.rootPath}">'

	def __hash__(self):
		return hash((self.rootPath, self.slug))

	def __eq__(self, other):
		try:
			return self.serial == other.serial
		except:
			return False

	def elements(self, accept: Optional[list[str]] = None) -> list[str]:
		accept = accept or _ACCEPT
		result, pattern = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + pattern +
			"))+[\'\"]?", json.dumps(self, cls = TodayEncoder)) if i[0] not in result]
		return result

	async def getSchedules(self, store: Store, ensure: bool = True, semaphore: Optional[asyncio.Semaphore] = None) -> list[Schedule]:

		if semaphore is not None:
			await semaphore.acquire()
		r = await request(
			session = _get_session(),
			url = (API["collection"]["store"] if ensure else API["collection"]["nearby"]).format(
				STORESLUG = store.slug, COLLECTIONSLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)
		if semaphore is not None:
			semaphore.release()

		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = []
		async with asyncio.TaskGroup() as tg:
			schedules = raw["schedules"]
			for i in raw["schedules"]:
				courseId = schedules[i]["courseId"]
				storeNum = schedules[i]["storeNum"]
				if (self.slug in [m["collId"] for m in raw["heroGallery"] if m["heroType"] == "TAG"]) and \
				((not ensure) or (storeNum == store.sid) or ("VIRTUAL" in raw["courses"][courseId]["type"])):
					tasks.append(tg.create_task(getSchedule(
						scheduleId = i, raw = schedules[i],
						rootPath = store.rootPath, slug = self.slug,
						store = getStore(
							sid = storeNum, rootPath = store.rootPath,
							raw = raw["stores"][storeNum] if storeNum in raw["stores"] else None),
						course = await getCourse(
							courseId = courseId, raw = raw["courses"][courseId], rootPath = store.rootPath,
							moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"], fuzzy = False))))
		return [t.result() for t in tasks]

	async def getRootSchedules(self, rootPath: Optional[str] = None) -> list[list[Schedule]]:
		rootPath = rootPath or self.rootPath
		stores = storeReturn(todayNation[rootPath], remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(_SEMAPHORE_LIMIT)
		tasks = [self.getSchedules(getStore(sid = i.sid, store = i, rootPath = rootPath), semaphore = semaphore) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getCourses(self, rootPath: Optional[str] = None) -> list[Course]:
		courses = []
		schedules = await self.getRootSchedules(rootPath = rootPath)
		for store in schedules:
			for schedule in store:
				if schedule.course not in courses:
					courses.append(schedule.course)
		return courses

async def getCollection(slug: str, rootPath: Optional[str] = None) -> Collection:
	global savedToday
	saved = list(savedToday["Collection"])
	assert rootPath is not None, "slug, rootPath 必须全部提供"
	keyword = f"{rootPath}/{slug}"
	for i in saved:
		if keyword == i:
			return savedToday["Collection"][i]

	get = await Collection(rootPath = rootPath, slug = slug)
	savedToday["Collection"][keyword] = get
	return get

class Sitemap():

	def match_by_assure(self, slug: str) -> bool:
		for s in knownSlugs:
			if s == slug:
				return False
		return True

	def match_by_valid(self, slug: str) -> bool:
		matches = re.findall(_VALIDDATES, slug)
		return matches and _validDates(matches[0][1], self.runtime) != []

	def __init__(self, rootPath: Optional[str] = None, flag: Optional[str] = None):
		assert rootPath is not None or flag, "rootPath 和 flag 必须提供一个"
		match rootPath, flag:
			case _, fl if fl is not None:
				self.urlPath = allRegions[fl]["storeURL"]
			case rp, _ if rp is not None:
				self.urlPath = rp.replace("/cn", ".cn")
		if knownSlugs == []:
			self.using = self.match_by_valid
		else:
			self.using = self.match_by_assure
		self.runtime = datetime.now()

	def __hash__(self):
		return hash(self.urlPath)

	def __eq__(self, other):
		try:
			return self.urlPath == other.urlPath
		except:
			return False

	def __repr__(self):
		return f'<Sitemap "{self.urlPath}">'

	async def getObjects(self) -> list[Course | Schedule]:
		r = await request(
			session = _get_session(),
			url = f"https://www.apple.com{self.urlPath}/today/sitemap.xml",
			ensureAns = False, timeout = _TIMEOUT, retryNum = _RETRYNUM)
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
			objects.append(parseURL(parsing, coro = True))

		return await asyncio.gather(*objects, return_exceptions = True)

def parseURL(url: str, coro: bool = False) -> dict:
	coursePattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*))"
	schedulePattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*)/([67][0-9]{18})(\/\?sn\=(R[0-9]{3}))?)"
	collectionPattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/collection/([a-z0-9\-]*))(/\S*)?"

	async def nothing():
		return None

	match [re.findall(p, url, re.I) for p in [schedulePattern, coursePattern, collectionPattern]]:
		case [[s, *_], _, _]:
			matched = {
				"parse": {
					"type": "schedule", "rootPath": s[1].replace(".cn", "/cn"),
					"slug": s[2], "scheduleId": s[3], "sid": s[5],
					"url": f"https://www.apple.com{s[1]}/today/event/{s[2]}/{s[3]}/?sn={s[5]}"},
				"coroutine": getSchedule}
		case [_, [c, *_], _]:
			matched = {
				"parse": {
					"type": "course", "rootPath": c[1].replace(".cn", "/cn"),
					"slug": c[2], "url": f"https://www.apple.com{c[1]}/today/event/{c[2]}"},
				"coroutine": getCourse}
		case [_, _, [c, *_]]:
			matched = {
				"parse": {
					"type": "collection", "rootPath": c[1].replace(".cn", "/cn"),
					"slug": c[2], "url": f"https://www.apple.com{c[1]}/today/collection/{c[2]}"},
				"coroutine": getCollection}
		case _:
			matched = {"parse": None}

	if not coro:
		return matched["parse"]
	if not matched["parse"]:
		return nothing()
	return matched["coroutine"](**{k: v for k, v in matched["parse"].items() if k not in ["type", "url", "sid"]})

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
		"MAIN2": "#TodayatApple {NEW}{TYPE}\n\n{PREFIX}*{NAME}*\n\n🗺️ {LOCATION}\n🕘 {TIME}\n\n{INTROTITLE}\n{INTRO}\n\n{SIGNPREFIX}\n{SIGN}"
	},
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
		"MAIN2": "#TodayatApple {NEW}{TYPE}\n\n{PREFIX}*{NAME}*\n\n🗺️ {LOCATION}\n🕘 {TIME}\n\n{INTROTITLE}\n{INTRO}\n\n{SIGNPREFIX}\n{SIGN}"
	}
}

def teleinfo(course: Optional[Course] = None, schedules: list[Schedule] = [], collection: Optional[Collection] = None,
	mode: str = "new", userLang: bool = True, prior: list[str] = []) -> tuple[str, str, list[list[list[str]]]]:
	runtime = datetime.now()
	offset = runtime.astimezone().utcoffset().total_seconds() / 3600
	priorlist = prior + list(allRegions)

	if collection is not None:
		text = disMarkdown(lang[userLang]["MAIN1"].format(
			NEW = lang[userLang]["NEW"] if mode == "new" else '',
			TYPE = lang[userLang]["COLLECTION"],
			NAME = collection.name,
			INTROTITLE = lang[userLang]["INTRO_COLLECTION"],
			INTRO = collection.description['long'],
		))
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
		storeCounts = {r: len(list(filter(lambda s: s.flag == r, storeSets))) for r in priorlist}
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
			if priorSchedule.timeStart.utcoffset().total_seconds() / 3600 != offset:
				tzText = " " + timezoneText(priorSchedule.timeStart)

		timing = lang[userLang]["START_FROM" if len(schedules) == 1 else "START_FROM_ALL"].format(
			START = priorSchedule.datetimeStart(form = lang[userLang]["FORMAT_START"]),
			END = priorSchedule.datetimeEnd(form = lang[userLang]["FORMAT_END"]), TZTEXT = tzText)
		keyboard = [[[lang[userLang]["SIGN_UP"], priorSchedule.url]]]
	else:
		try:
			date = re.findall(_VALIDDATES, course.slug)[0][1]
			vals = _validDates(date, runtime)
			timing = f' {lang[userLang]["OR"]} '.join([i.strftime(lang[userLang]["FORMAT_DATE"]) for i in vals])
		except IndexError:
			timing = lang[userLang]["GENERAL_TIMING"]
		keyboard = [[[lang[userLang]["LEARN_COURSE"], course.url]]]

	keyboard[0].append([lang[userLang]["DOWNLOAD_IMAGE"], course.images["landscape"]])

	if mode == "new" or schedules == []:
		signing = signingPrefix = ""
	else:
		rsvp = [i.status for i in schedules]
		upCount = rsvp.count(True)
		seCount = len(schedules)
		if seCount > 1:
			if upCount:
				if upCount == seCount:
					signing = lang[userLang]["SIGN_UP_ALL"]
				else:
					signing = lang[userLang]["SIGN_UP_SOME"].format(AOK = upCount, AALL = seCount)
			else:
				signing = lang[userLang]["SIGN_UP_NONE"]
		else:
			signing = lang[userLang]["SIGN_UP_SINGLE"] if upCount else lang[userLang]["SIGN_UP_NOT"]
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
		SIGN = signing
	)).strip("\n")

	image = course.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"

	return text, image, keyboard