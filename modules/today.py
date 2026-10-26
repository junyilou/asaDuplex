import asyncio
import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import (Any, ClassVar, Final, Literal,
                    Required, Self, TypedDict, cast)
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from modules.regions import Regions
from modules.util import (AsyncGather, CoroutineType, SemaphoreType,
                          SessionType, browser_agent, get_session,
                          request, with_semaphore)
from storeInfo import Store as RawStore
from storeInfo import getStore as get_raw_store
from storeInfo import storeReturn

ACCEPT: Final = ("jpg", "png", "mp4", "mov", "pages", "key", "pdf")
PARAM: Final[dict[str, Any]] = {"method": "GET", "timeout": 25, "retry": 5}
SEMAPHORE_LIMIT: Final = 20
DATE_FRAGMENT_PATTERN: Final = r"(-([0-9]{4,8}))$"

GRAPH: dict[str, list[str]] = {}
LEADERBOARD: dict[str, int] = {}

ROOT_TO_FLAG: dict[str, str] = {v.url_taa: k for k, v in Regions.items() if v.url_taa is not None}

type JSONDict = dict[str, Any]
type VideoMap = dict[str, dict[str, Any]]

class RawImage(TypedDict):
	source: str

class RawImageSet(TypedDict):
	portrait: RawImage
	landscape: RawImage

class RawAmbientVideo(TypedDict, total = False):
	sources: list[str]
	poster: list[RawImageSet]

class RawMedia(TypedDict, total = False):
	images: list[RawImageSet]
	ambientVideo: RawAmbientVideo

class RawTalent(TypedDict, total = False):
	name: Required[str]
	title: str
	description: str
	backgroundImage: str
	logo: str
	websiteUrl: str
	url: str
	socialLinks: list[dict[str, str]]

class RawCourse(TypedDict, total = False):
	type: str
	name: Required[str]
	title: str
	urlTitle: Required[str]
	longDescription: str
	mediumDescription: str
	shortDescription: str
	backgroundMedia: RawMedia
	modalVideo: dict[str, Any]
	collectionName: str
	collId: str
	talentType: str
	programType: str

class RawSchedule(TypedDict, total = False):
	id: str
	courseId: Required[str]
	startTime: int | float
	endTime: int | float
	storeNum: Required[str]
	status: str
	displayStartTime: str
	displayEndTime: str
	icalUrl: str

class RawStorePayload(TypedDict, total = False):
	storeNum: Required[str]
	name: Required[str]
	slug: Required[str]
	path: str
	city: str
	state: str
	lat: float
	long: float
	timezone: dict[str, str]

class RawHero(TypedDict, total = False):
	name: str
	title: str
	collId: str
	heroType: str
	backgroundMedia: RawMedia

class RawLanding(TypedDict, total = False):
	courses: dict[str, RawCourse]
	schedules: dict[str, RawSchedule]
	stores: dict[str, RawStorePayload]

class RawCourseSession(RawLanding, total = False):
	talents: list[RawTalent]
	moreAbout: RawHero
	heroGallery: list[RawHero]

class RawCollectionPayload(RawLanding, total = False):
	name: Required[str]
	longDescription: str
	mediumDescription: str
	shortDescription: str
	heroGallery: list[RawHero]
	inCollaborationWith: dict[str, Any]
	courseList: list[str]

class ParsedURL(TypedDict, total = False):
	type: Required[Literal["schedule", "course", "collection"]]
	root_path: Required[str]
	slug: Required[str]
	scheduleId: str
	sid: str
	url: str

class TodayAPIError(ValueError):
	"""Apple Today at Apple BFF 请求失败或返回数据无效。"""

	def __init__(self, url: str, detail: str = "") -> None:
		self.url = url
		self.detail = detail
		detail_text = f"{detail}: " if detail else ""
		super().__init__(f"{detail_text}{url}")

def clean_text(value: Any) -> str:
	if not isinstance(value, str):
		return ""
	return re.sub(r"\s*\n\s*", " ", value.strip())

def normalize_text(text: str) -> str:
	rep = {0xa0: 0x20, 0x200b: None, 0x200c: None, 0x2060: None}
	return text.translate(rep)

async def fetch_text(url: str, session: SessionType | None = None,
	semaphore: SemaphoreType | None = None) -> str:
	"""请求 Apple 文本响应，并在返回前检查 HTTP 状态码。"""
	try:
		async with with_semaphore(semaphore):
			result = await request(url, session = session, mode = ["text", "status"],
				headers = browser_agent, **PARAM)
	except Exception as exp:
		raise TodayAPIError(url, "request failed") from exp
	status = cast(int, result["status"])
	if status != 200:
		raise TodayAPIError(url, f"HTTP {status}")
	return cast(str, result["text"])

async def fetch_json[T](url: str, session: SessionType | None = None,
	semaphore: SemaphoreType | None = None) -> T:
	"""请求 Apple JSON 响应，并清理不可见空白字符。"""
	text = await fetch_text(url, session = session, semaphore = semaphore)
	try:
		data = json.loads(normalize_text(text))
	except json.JSONDecodeError as exp:
		raise TodayAPIError(url, "invalid JSON") from exp
	if not isinstance(data, dict):
		raise TodayAPIError(url, "expected a JSON object")
	return cast(T, data)

class APIClass:
	def __init__(self, parts: Sequence[str]) -> None:
		self._parts: list[str] = list(parts)
		self.args = {
			"COLLECTIONSLUG": "collectionSlug",
			"COURSESLUG": "courseSlug",
			"ROOTPATH": "stageRootPath",
			"SCHEDULEID": "scheduleId",
			"STORESLUG": "storeSlug"}

	def __getitem__(self, key: str) -> Self:
		return type(self)(parts = self._parts + [key])

	def __repr__(self) -> str:
		return "/".join(self._parts)

	def format(self, **kwargs: Any) -> str:
		return "/".join(self._parts) + "?" + "&".join(
			f"{self.args.get(k, k)}={v}" for k, v in kwargs.items())

API = APIClass(["https:", "", "www.apple.com", "today-bff"])

def generate_leaderboard(db_filename: str) -> dict[int, list[str]]:
	import math

	from modules.michael import Store as MSStore
	from modules.michael import loads

	def calculate_bonus(store: MSStore) -> int:
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

	with open(db_filename) as r:
		db = loads(json.load(r))
	for rid, store in db.items():
		LEADERBOARD[f"R{rid}"] = calculate_bonus(store)
	return {point: sorted(k for k, v in LEADERBOARD.items() if v == point)
		for point in sorted(set(LEADERBOARD.values()))}

@lru_cache(maxsize = 1)
def known_slugs() -> frozenset[str]:
	try:
		with open("Retail/assured-events.json") as r:
			assure = json.load(r)
		return frozenset(assure.values())
	except FileNotFoundError:
		return frozenset()

def parse_resolution(vids: Sequence[str], direction: Literal["l", "p"] | None = None) -> list[str]:
	res: dict[str, tuple[int, int]] = {}
	for video in vids:
		found = re.findall(r"([0-9]+)x([0-9]+)\.[a-zA-Z0-9]+", video)
		if not found:
			return list(vids)
		res[video] = int(found[0][0]), int(found[0][1])
	ordered = sorted(vids, key = lambda key: res[key][0] * res[key][1], reverse = True)
	if direction not in ("p", "l"):
		return ordered
	return [video for video in ordered
		if direction == "p" and res[video][0] < res[video][1]
		or direction == "l" and res[video][0] > res[video][1]]

def load_graph() -> dict[str, list[str]]:
	if not GRAPH:
		try:
			with open("Retail/taa-graph.json") as r:
				GRAPH.update(json.load(r))
		except Exception:
			pass
	return GRAPH

def load_leaderboard() -> None:
	if not LEADERBOARD:
		try:
			generate_leaderboard("Retail/facades.json")
		except Exception:
			pass

def covering_seeds(rids: Iterable[str], graph: Mapping[str, Sequence[str]]) -> list[str]:
	"""从给定门店中选出一个较小的支配集。"""
	remaining = set(rids)
	if not remaining:
		return []
	try:
		from modules.dominating import get_dominating_set
	except Exception:
		return sorted(remaining)
	subgraph = {
		rid: [neighbor for neighbor in graph.get(rid, ()) if neighbor in remaining]
		for rid in remaining
	}
	for rid, neighbors in subgraph.items():
		if rid not in neighbors:
			neighbors.append(rid)
	sets = [get_dominating_set(subgraph, rid) for rid in sorted(remaining)]
	load_leaderboard()
	best = min(sets, key = lambda group: (
		len(group),
		-sum(LEADERBOARD.get(rid, 0) for rid in group),
		sorted(group)))
	return sorted(best)

def peer_stores(stores: list[RawStore], fast: bool = False) -> list[RawStore]:
	if not fast:
		return stores
	try:
		from modules.dominating import get_dominating_set
	except Exception:
		return stores
	graph = load_graph()
	if not graph:
		return stores
	load_leaderboard()
	results: dict[str, list[str]] = {}
	mapping = {s.rid: s for s in stores}
	subgraph = {s: graph.get(s, []) for s in mapping}
	sets = [get_dominating_set(subgraph, store) for store in mapping]
	sets.sort(key = lambda s: (len(s), -sum(LEADERBOARD.get(store, 0) for store in s)))
	results.update({a: graph.get(a, []) for a in sorted(sets[0])})
	return [i for i in [get_raw_store(s) for s in results] if i]

def date_candidates(ex: str, runtime: datetime) -> list[date]:
	result: list[date] = []
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
			parsed = datetime.strptime(ex, pattern).date()
		except ValueError:
			continue
		delta = (parsed - runtime.date()).days
		if parsed not in result and -21 < delta < 70:
			result.append(parsed)
	return result

class TodayObject:
	hash_fields: ClassVar[tuple[str, ...]] = ()
	sort_fields: ClassVar[tuple[str, ...]] = ()
	raw: dict[str, Any]

	def sort_tuple(self) -> tuple[Any, ...]:
		return tuple(getattr(self, key) for key in self.sort_fields)

	def __hash__(self) -> int:
		return hash((self.__class__.__name__,
			*(getattr(self, attr) for attr in self.hash_fields)))

	def __lt__(self, other: object) -> bool:
		if type(self) is not type(other) or not isinstance(other, TodayObject):
			return False
		return self.sort_tuple() < other.sort_tuple()

	def __gt__(self, other: object) -> bool:
		if type(self) is not type(other) or not isinstance(other, TodayObject):
			return False
		return self.sort_tuple() > other.sort_tuple()

	def __eq__(self, other: object) -> bool:
		if type(self) is not type(other) or not isinstance(other, TodayObject):
			return False
		return self.sort_tuple() == other.sort_tuple()

class TodayEncoder(json.JSONEncoder):
	def __init__(self, *, ensure_ascii: bool = False, **kwargs: Any) -> None:
		super().__init__(ensure_ascii = ensure_ascii, **kwargs)

	def default(self, o: Any) -> Any:
		if isinstance(o, (TodayObject, RawStore)):
			return o.raw
		return super().default(o)

class Talent(TodayObject):
	hash_fields: ClassVar[tuple[str, ...]] = ("name",)
	sort_fields: ClassVar[tuple[str, ...]] = ("name",)

	def __init__(self, raw: Mapping[str, Any]) -> None:
		self.raw: dict[str, Any] = dict(raw)
		self.name: str = clean_text(raw.get("name")) or "Unknown"
		title = clean_text(raw.get("title"))
		description = clean_text(raw.get("description"))
		self.title: str | None = title or None
		self.description: str | None = description or None
		image = raw.get("backgroundImage") or raw.get("logo")
		self.image: str | None = image if isinstance(image, str) and image else None
		links: dict[str, str] = {}
		if isinstance(raw.get("websiteUrl"), str):
			links["website"] = raw["websiteUrl"]
		if isinstance(raw.get("url"), str):
			links["url"] = raw["url"]
		for social in raw.get("socialLinks") or []:
			if isinstance(social, Mapping):
				name, url = social.get("name"), social.get("url")
				if isinstance(name, str) and isinstance(url, str):
					links[name] = url
		self.links: dict[str, str] = links

	def __repr__(self) -> str:
		return f"<Talent \"{self.name}\"" + (f", \"{self.title}\"" if self.title else "") + ">"

class TodayMedia(TodayObject):
	description: dict[str, str]
	images: dict[str, str]
	videos: VideoMap
	talents: list[Talent]

	def load_description(self, raw: Mapping[str, Any]) -> None:
		self.description = {
			key: clean_text(raw.get(f"{key}Description"))
			for key in ("long", "medium", "short")}

	@staticmethod
	def media_source(node: Any, orientation: str) -> str:
		if not isinstance(node, Mapping):
			return ""
		value = node.get(orientation)
		if not isinstance(value, Mapping):
			return ""
		source = value.get("source")
		return source if isinstance(source, str) else ""

	def load_media(self, media: Mapping[str, Any] | None) -> None:
		images = media.get("images") if isinstance(media, Mapping) else None
		first = images[0] if isinstance(images, list) and images else {}
		self.images = {
			"portrait": self.media_source(first, "portrait"),
			"landscape": self.media_source(first, "landscape")}
		self.videos = {}
		ambient = media.get("ambientVideo") if isinstance(media, Mapping) else None
		if not isinstance(ambient, Mapping):
			return
		sources = [source for source in ambient.get("sources") or [] if isinstance(source, str)]
		if not sources:
			return
		posters = ambient.get("poster") or []
		poster = posters[0] if isinstance(posters, list) and posters else {}
		for orientation, letter in (("portrait", "p"), ("landscape", "l")):
			self.videos[orientation] = {
				"poster": self.media_source(poster, orientation),
				"videos": parse_resolution(sources, letter)}

	def load_talents(self, talents: Iterable[Mapping[str, Any]] | None) -> None:
		self.talents = [Talent(raw = talent) for talent in talents or []
			if isinstance(talent, Mapping)]

	def elements(self, accept: Sequence[str] | None = None) -> list[str]:
		accept = accept or ACCEPT
		pattern = "|".join(accept)
		serialized = json.dumps(self, cls = TodayEncoder)
		matches = re.findall(r"[\'\"](http[^\"\']*\.(" + pattern + "))+[\'\"]?", serialized)
		return list(dict.fromkeys(match[0] for match in matches))

class SessionEntry(TodayMedia):
	"""Course 和 Collection 共用的排课查询逻辑。"""
	slug: str
	root_path: str
	flag: str

	async def get_schedules(self, store: Store, ensure: bool = True,
		date: datetime | None = None,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[Schedule]:
		raise NotImplementedError

	async def get_multiple_schedules(self,
		raw_stores: Sequence[RawStore] | None = None,
		stores: Sequence[Store] | None = None,
		date: datetime | None = None,
		fast: bool = True, ensure: bool = True,
		session: SessionType | None = None) -> list[Schedule]:
		"""查询一个或多个门店的排课。

		ensure=True 时只保留目标门店的排课；False 时也保留 nearby endpoint 返回的
		其他门店排课。
		"""
		if stores:
			wrapped = list(stores)
			raw = [store.raw_store for store in wrapped]
		elif raw_stores:
			raw = list(raw_stores)
			wrapped = [Store(store = store) for store in raw]
		else:
			return []
		if not raw:
			return []
		root_paths = {store.raw_store: store.root_path for store in wrapped}
		allowed = {store.rid for store in raw}
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as ses:
			tasks = (
				self.get_schedules(
					Store(store = peer, root_path = root_paths.get(peer) or peer.region.url_taa or self.root_path),
					ensure = False, date = date, session = ses, semaphore = semaphore)
				for peer in peer_stores(raw, fast)
			)
			results = await AsyncGather(tasks, return_exceptions = True)
		return sorted({
			schedule for result in results if not isinstance(result, Exception)
			for schedule in result
			if not ensure or schedule.raw_store.rid in allowed
		})


def raw_store_from_payload(raw: Mapping[str, Any], root_path: str | None) -> RawStore | None:
	"""本地数据库缺少某个门店时，用 Apple 返回的数据构造 storeInfo.Store。"""
	store_num = str(raw.get("storeNum") or "")
	if not store_num:
		return None
	data = dict(raw)
	flag = data.get("flag") or ROOT_TO_FLAG.get(root_path or "")
	if not isinstance(flag, str) or not flag:
		return None
	data["flag"] = flag
	timezone = data.get("timezone")
	if isinstance(timezone, Mapping):
		data["timezone"] = timezone.get("name", "")
	for key in ("city", "name", "state"):
		if not isinstance(data.get(key), str):
			return None
	try:
		return RawStore(rid = store_num, dct = cast(Any, data))
	except Exception:
		return None

class Store(TodayObject):
	hash_fields: ClassVar[tuple[str, ...]] = ("sid",)
	sort_fields: ClassVar[tuple[str, ...]] = ("raw_store",)

	def __init__(self,
		raw: Mapping[str, Any] | None = None,
		root_path: str | None = None,
		sid: int | str | None = None,
		store: RawStore | None = None) -> None:

		if raw is not None:
			if root_path is None:
				path = raw.get("path")
				if isinstance(path, str) and "/retail/" in path:
					root_path = path.split("/retail/", 1)[0]
			store_num = str(raw.get("storeNum") or "")
			raw_store = get_raw_store(store_num) or raw_store_from_payload(raw, root_path)
			if raw_store is None:
				raise ValueError(f"本地数据库中无法匹配关键字 {store_num!r}")
			self.name: str = clean_text(raw.get("name")) or raw_store.name
			self.sid: str = store_num
			self.slug: str = str(raw.get("slug") or raw_store.slug or "")
			timezone = raw.get("timezone")
			self.timezone: str = (
				timezone.get("name") if isinstance(timezone, Mapping) else "") \
				or (raw_store.timezone.key if raw_store.timezone else "")
			path = raw.get("path")
			if isinstance(path, str) and root_path == "/cn" and path.startswith("/cn/"):
				path = path.removeprefix("/cn")
			domain = "https://www.apple.com.cn" if root_path == "/cn" else "https://www.apple.com"
			self.url: str = f"{domain}{path}" if isinstance(path, str) and path else (raw_store.url or "")
			lat, long = raw.get("lat"), raw.get("long")
			self.coord: list[float] | None = (
				[float(lat), float(long)] if isinstance(lat, (int, float))
				and isinstance(long, (int, float)) else None)
		else:
			raw_store = store or (get_raw_store(sid) if sid is not None else None)
			if raw_store is None:
				raise ValueError(f"本地数据库中无法匹配关键字 {sid!r}")
			self.name = raw_store.name
			self.sid = raw_store.rid
			self.slug = raw_store.slug or ""
			self.timezone = raw_store.timezone.key if raw_store.timezone else ""
			self.url = raw_store.url or ""
			self.coord = None

		if not self.slug:
			raise ValueError(f"零售店 {self.sid} 缺少 slug")
		if not self.timezone:
			raise ValueError(f"零售店 {self.sid} 缺少时区")
		self.raw_store: RawStore = raw_store
		root = root_path or raw_store.region.url_taa
		if root is None:
			raise ValueError(f"零售店 {self.sid} 缺少 root_path")
		self.root_path: str = root
		self.flag: str = ROOT_TO_FLAG.get(root, raw_store.flag)
		self.today: str = self.url.replace("/retail/", "/today/")
		self.calendar: str = self.url.replace("/retail/", "/today/calendar/")
		self.serial: dict[str, str] = {"sid": self.sid}
		self.raw: dict[str, Any] = {k: v for k, v in vars(self).items() if k != "raw"}

	@property
	def city(self) -> str:
		return self.raw_store.city

	@property
	def state(self) -> str:
		return self.raw_store.state

	@property
	def rid(self) -> str:
		return self.raw_store.rid

	@property
	def name_eng(self) -> str:
		return self.raw_store.name_eng

	@property
	def region(self) -> Any:
		return self.raw_store.region

	@property
	def is_open(self) -> bool:
		return self.raw_store.isOpen

	def __repr__(self) -> str:
		return f"<Store \"{self.name}\" ({self.sid}), \"{self.slug}\", \"{self.root_path}\">"

	async def landing(self, ensure: bool, session: SessionType | None,
		semaphore: SemaphoreType | None) -> RawLanding:
		endpoint = API["landing"]["store" if ensure else "nearby"]
		url = endpoint.format(STORESLUG = self.slug, ROOTPATH = self.root_path,
			**({} if ensure else {"nearby": "true"}))
		return await fetch_json(url, session = session, semaphore = semaphore)

	async def get_courses(self, ensure: bool = True,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[Course]:
		remote = await self.landing(ensure, session, semaphore)
		courses = remote.get("courses") or {}
		if not isinstance(courses, Mapping):
			raise TodayAPIError(f"store {self.sid}", "missing courses")
		tasks = [
			Course.get(root_path = self.root_path, slug = course["urlTitle"],
				remote = remote, session = session)
			for course in courses.values()
			if isinstance(course, Mapping) and isinstance(course.get("urlTitle"), str)]
		return await AsyncGather(tasks)

	async def get_schedules(self, ensure: bool = True,
		date: datetime | None = None,
		covered_store_list: list[str] | None = None,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[Schedule]:
		remote = await self.landing(ensure, session, semaphore)
		schedules = remote.get("schedules") or {}
		courses = remote.get("courses") or {}
		if not isinstance(schedules, Mapping) or not isinstance(courses, Mapping):
			raise TodayAPIError(f"store {self.sid}", "missing schedules")
		tasks: list[CoroutineType[Schedule]] = []
		for schedule_id, raw_schedule in schedules.items():
			if not isinstance(raw_schedule, Mapping):
				continue
			course = courses.get(raw_schedule.get("courseId"))
			if not isinstance(course, Mapping):
				continue
			if ensure and raw_schedule.get("storeNum") != self.sid:
				continue
			tasks.append(Schedule.get(root_path = self.root_path, scheduleId = schedule_id,
				slug = course["urlTitle"], remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [schedule for schedule in results
				if schedule.naive_start.date() == date.date()]
		if covered_store_list is not None:
			stores = remote.get("stores") or {}
			covered_store_list.clear()
			covered_store_list.extend(stores)
		return results

	@classmethod
	async def get_schedules_for_stores(cls,
		stores: Sequence[RawStore | Store],
		*,
		include_nearby: bool = False,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None,
		graph: Mapping[str, Sequence[str]] | None = None) -> list[Schedule]:
		"""按 graph 覆盖迭代查询多个门店的排课。

		每轮从未覆盖门店中选出支配集，请求这些 seed 的 nearby endpoint，再把响应
		中出现的门店标记为已覆盖。最终只能自己作为 seed 的门店只请求一次并视为
		最终结果，避免 graph 覆盖不全时反复请求。
		"""
		wrapped: dict[str, Store] = {}
		for item in stores:
			store = item if isinstance(item, Store) else cls(store = item)
			wrapped[store.sid] = store
		if not wrapped:
			return []
		selected = set(wrapped)
		graph = load_graph() if graph is None else graph
		semaphore = semaphore or asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as ses:
			if not graph:
				results = await asyncio.gather(*(
					store.get_schedules(ensure = not include_nearby,
						session = ses, semaphore = semaphore)
					for store in wrapped.values()), return_exceptions = True)
				return sorted({*result for result in results
					if not isinstance(result, BaseException)})
			schedules: set[Schedule] = set()
			remaining = set(selected)
			while remaining:
				seeds = covering_seeds(remaining, graph)
				if not seeds:
					seeds = [min(remaining)]
				covered_lists: list[list[str]] = []
				tasks: list[CoroutineType[list[Schedule]]] = []
				for rid in seeds:
					covered: list[str] = []
					covered_lists.append(covered)
					tasks.append(wrapped[rid].get_schedules(ensure = False,
						covered_store_list = covered, session = ses,
						semaphore = semaphore))
				responses = await asyncio.gather(*tasks, return_exceptions = True)
				for rid, covered, response in zip(seeds, covered_lists,
					responses, strict = True):
					if not isinstance(response, BaseException):
						schedules.update(schedule for schedule in response
							if include_nearby or schedule.store.sid in selected)
					reached = {sid for sid in covered if sid in remaining}
					reached.add(rid)
					remaining.difference_update(reached)
			return sorted(schedules)

	async def get_coords(self, session: SessionType | None = None) -> list[float]:
		detail = await self.raw_store.detail(session = session)
		geo = detail.get("geolocation") or {}
		self.coord = [point[1] for point in sorted(geo.items())]
		return self.coord

	async def get_covering_stores(self, graph: MutableMapping[str, list[str]] | None = None,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[str]:
		results: list[str] = []
		_ = await self.get_schedules(ensure = False, covered_store_list = results,
			session = session, semaphore = semaphore)
		results = sorted(result for result in results
			if (store := get_raw_store(result)) and store.isOpen)
		if graph is not None:
			graph[self.sid] = results
		return results

class Schedule(TodayObject):
	hash_fields: ClassVar[tuple[str, ...]] = ("root_path", "scheduleId", "slug")
	sort_fields: ClassVar[tuple[str, ...]] = ("naive_start", "scheduleId")
	course: Course

	@classmethod
	async def get(cls,
		root_path: str,
		scheduleId: str,
		slug: str,
		remote: Mapping[str, Any] | None = None,
		session: SessionType | None = None) -> Self:
		schedule_id = str(scheduleId)
		if remote is None:
			url = API["session"]["schedule"].format(
				COURSESLUG = slug, SCHEDULEID = schedule_id, ROOTPATH = root_path)
			remote = await fetch_json(url, session = session)
		schedules = remote.get("schedules") or {}
		courses = remote.get("courses") or {}
		stores = remote.get("stores") or {}
		raw_schedule = schedules.get(schedule_id)
		if not isinstance(raw_schedule, Mapping):
			raise TodayAPIError(f"schedule {root_path}/{slug}/{schedule_id}",
				"missing schedule")
		store_num = str(raw_schedule.get("storeNum") or "")
		store_raw = stores.get(store_num)
		if isinstance(store_raw, Mapping):
			store = Store(raw = store_raw, root_path = root_path)
		else:
			store = Store(sid = store_num, root_path = root_path)
		course_raw = courses.get(raw_schedule.get("courseId"))
		if not isinstance(course_raw, Mapping):
			raise TodayAPIError(f"schedule {root_path}/{slug}/{schedule_id}",
				"missing course")
		course = await Course.get(root_path = root_path,
			slug = str(course_raw.get("urlTitle") or ""), remote = remote,
			session = session)
		return cls(scheduleId = schedule_id, course = course, store = store,
			root_path = root_path, raw = raw_schedule)

	def __init__(self,
		course: Course,
		scheduleId: str,
		store: Store,
		raw: Mapping[str, Any],
		root_path: str) -> None:

		self.course = course
		self.scheduleId = str(scheduleId)
		self.store = store
		self.root_path = root_path
		self.slug = course.slug
		self.flag = ROOT_TO_FLAG.get(root_path, course.flag)
		self.timezone = store.timezone
		self.tzinfo = ZoneInfo(self.timezone)
		start = cast(int | float, raw["startTime"])
		end = cast(int | float, raw["endTime"])
		self.start_time = datetime.fromtimestamp(start / 1000, tz = self.tzinfo)
		self.end_time = datetime.fromtimestamp(end / 1000, tz = self.tzinfo)
		self.naive_start = self.start_time.replace(tzinfo = None)
		self.naive_end = self.end_time.replace(tzinfo = None)
		self.status: bool = raw.get("status") == "RSVP"
		self.serial: dict[str, str] = {
			"slug": self.slug, "scheduleId": self.scheduleId, "root_path": self.root_path}
		self.url = (f"https://www.apple.com{root_path.replace("/cn", ".cn")}"
			f"/today/event/{self.slug}/{self.scheduleId}/?sn={self.store.sid}")
		self.raw: dict[str, Any] = dict(raw) | {"serial": self.serial}

	@property
	def raw_store(self) -> RawStore:
		return self.store.raw_store

	def __getattr__(self, name: str) -> Any:
		"""让 Schedule 继续表现得像 Course，但不复制所有属性。"""
		course = self.__dict__.get("course")
		if course is not None:
			return getattr(course, name)
		raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

	def format_start(self, form: str = "%-m 月 %-d 日 %-H:%M") -> str:
		return f"{self.start_time or self.naive_start:{form}}"

	def format_end(self, form: str = "%-H:%M") -> str:
		return f"{self.end_time or self.naive_end:{form}}"

	def __repr__(self) -> str:
		return (f"<Schedule {self.scheduleId} of {self.course.courseId}, "
			f"{self.format_start("%-m/%-d %-H:%M")}-{self.format_end()} @ {self.store.sid}>")

class Course(SessionEntry):
	hash_fields: ClassVar[tuple[str, ...]] = ("root_path", "slug")
	sort_fields: ClassVar[tuple[str, ...]] = ("courseId", "root_path")
	collection: str | Collection | None

	@classmethod
	async def get(cls,
		root_path: str,
		slug: str,
		remote: Mapping[str, Any] | None = None,
		session: SessionType | None = None) -> Self:
		if remote is None:
			url = API["session"]["course"].format(COURSESLUG = slug, ROOTPATH = root_path)
			remote = await fetch_json(url, session = session)
		courses = remote.get("courses") or {}
		if not isinstance(courses, Mapping):
			raise TodayAPIError(f"course {root_path}/{slug}", "missing courses")
		course_id = next((cid for cid, course in courses.items()
			if isinstance(course, Mapping) and course.get("urlTitle") == slug), None)
		if course_id is None:
			raise TodayAPIError(f"course {root_path}/{slug}", "course not found")
		raw = courses[course_id]
		if not isinstance(raw, Mapping):
			raise TodayAPIError(f"course {root_path}/{slug}", "invalid course")
		talents = [talent for talent in remote.get("talents") or []
			if isinstance(talent, Mapping)]
		collection: str | Collection | None = raw.get("collectionName")
		candidates: list[Mapping[str, Any]] = []
		more_about = remote.get("moreAbout")
		if isinstance(more_about, Mapping):
			candidates.append(more_about)
		candidates.extend(gallery for gallery in remote.get("heroGallery") or []
			if isinstance(gallery, Mapping) and gallery.get("heroType") == "TAG")
		for candidate in candidates:
			if collection and collection in (candidate.get("name"), candidate.get("title")):
				coll_id = candidate.get("collId")
				if isinstance(coll_id, str):
					collection = await Collection.get(root_path = root_path,
						slug = coll_id, session = session)
					break
		return cls(courseId = course_id, raw = raw, root_path = root_path,
			collection = collection, talents = talents)

	def __init__(self,
		courseId: str,
		raw: Mapping[str, Any],
		root_path: str,
		collection: str | Collection | None = None,
		talents: Iterable[Mapping[str, Any]] = ()) -> None:

		self.root_path = root_path
		self.flag = ROOT_TO_FLAG.get(root_path, "")
		self.courseId = str(courseId)
		self.name = clean_text(raw.get("name"))
		self.title = clean_text(raw.get("title"))
		self.slug = str(raw.get("urlTitle") or "")
		if not self.name or not self.slug:
			raise ValueError(f"课程 {root_path}/{courseId} 信息不完整")
		self.serial: dict[str, str] = {"slug": self.slug, "root_path": self.root_path}
		self.collection = collection
		self.load_description(raw)
		self.intro: dict[str, str | list[str]] = {}
		modal = raw.get("modalVideo")
		if isinstance(modal, Mapping):
			poster = modal.get("poster")
			sources = modal.get("sources")
			if isinstance(poster, Mapping) and isinstance(poster.get("source"), str):
				self.intro["poster"] = poster["source"]
			if isinstance(sources, list):
				self.intro["video"] = parse_resolution(
					[source for source in sources if isinstance(source, str)])
		media = raw.get("backgroundMedia")
		self.load_media(media if isinstance(media, Mapping) else None)
		self.load_talents(talents)
		self.special: bool = (
			"SPECIAL" in str(raw.get("type") or "")
			or "HIGH" in str(raw.get("talentType") or ""))
		self.url = (f"https://www.apple.com{root_path.replace("/cn", ".cn")}"
			f"/today/event/{self.slug}")
		self.raw: dict[str, Any] = dict(raw) | {"serial": self.serial}

	def __repr__(self) -> str:
		col = (f", Collection <{self.collection.name}>"
			if isinstance(self.collection, Collection)
			else f", Collection \"{self.collection}\"") \
			if self.collection is not None else ""
		return f"<Course {self.courseId} \"{self.name}\", \"{self.slug}\"{col}>"

	async def get_schedules(self, store: Store, ensure: bool = True,
		date: datetime | None = None,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[Schedule]:
		endpoint = API["session"]["course"]["store" if ensure else "nearby"]
		url = endpoint.format(STORESLUG = store.slug, COURSESLUG = self.slug,
			ROOTPATH = store.root_path, **({} if ensure else {"nearby": "true"}))
		remote = await fetch_json(url, session = session,
			semaphore = semaphore)
		schedules = remote.get("schedules") or {}
		courses = remote.get("courses") or {}
		if not isinstance(schedules, Mapping) or not isinstance(courses, Mapping):
			raise TodayAPIError(f"course schedules {store.root_path}/{self.slug}/{store.slug}",
				"missing schedules")
		tasks: list[CoroutineType[Schedule]] = []
		for schedule_id, raw_schedule in schedules.items():
			if not isinstance(raw_schedule, Mapping):
				continue
			if raw_schedule.get("courseId") != self.courseId:
				continue
			if ensure and raw_schedule.get("storeNum") != store.sid:
				continue
			course = courses.get(raw_schedule.get("courseId"))
			if not isinstance(course, Mapping):
				continue
			tasks.append(Schedule.get(root_path = store.root_path, scheduleId = schedule_id,
				slug = self.slug, remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [schedule for schedule in results
				if schedule.naive_start.date() == date.date()]
		return results

	async def get_single_schedule(self, session: SessionType | None = None) -> Schedule:
		return await Schedule.get(scheduleId = self.courseId, root_path = self.root_path,
			slug = self.slug, session = session)

class Collection(SessionEntry):
	hash_fields: ClassVar[tuple[str, ...]] = ("root_path", "slug")
	sort_fields: ClassVar[tuple[str, ...]] = ("root_path", "slug")

	@classmethod
	async def get(cls,
		root_path: str,
		slug: str,
		remote: Mapping[str, Any] | None = None,
		session: SessionType | None = None) -> Self:
		if remote is None:
			url = API["collection"]["geo"].format(
				COLLECTIONSLUG = slug, ROOTPATH = root_path)
			remote = await fetch_json(url, session = session)
		if not isinstance(remote, Mapping) or "name" not in remote:
			raise TodayAPIError(f"collection {root_path}/{slug}", "invalid collection")
		return cls(root_path = root_path, slug = slug, raw = remote)

	def __init__(self,
		raw: Mapping[str, Any],
		root_path: str,
		slug: str) -> None:

		self.name = clean_text(raw.get("name"))
		self.slug = slug
		self.root_path = root_path
		self.flag = ROOT_TO_FLAG.get(root_path, "")
		self.url = (f"https://www.apple.com{root_path.replace("/cn", ".cn")}"
			f"/today/collection/{slug}/")
		self.serial: dict[str, str] = {"slug": slug, "root_path": root_path}
		self.load_description(raw)
		galleries = raw.get("heroGallery") or []
		first = galleries[0] if galleries and isinstance(galleries[0], Mapping) else {}
		media = first.get("backgroundMedia")
		self.load_media(media if isinstance(media, Mapping) else None)
		collab = raw.get("inCollaborationWith")
		if isinstance(collab, Mapping):
			talents = collab.get("partners") or []
		else:
			talents = raw.get("talents") or []
		self.load_talents(talents if isinstance(talents, Iterable) else [])
		self.raw: dict[str, Any] = dict(raw) | {"serial": self.serial}

	def __repr__(self) -> str:
		return f"<Collection \"{self.name}\", \"{self.slug}\", \"{self.root_path}\">"

	async def get_schedules(self, store: Store, ensure: bool = True,
		date: datetime | None = None,
		session: SessionType | None = None,
		semaphore: SemaphoreType | None = None) -> list[Schedule]:
		endpoint = API["collection"]["store" if ensure else "nearby"]
		url = endpoint.format(STORESLUG = store.slug, COLLECTIONSLUG = self.slug,
			ROOTPATH = store.root_path, **({} if ensure else {"nearby": "true"}))
		remote = await fetch_json(url, session = session,
			semaphore = semaphore)
		schedules = remote.get("schedules") or {}
		courses = remote.get("courses") or {}
		if not isinstance(schedules, Mapping) or not isinstance(courses, Mapping):
			raise TodayAPIError(
				f"collection schedules {store.root_path}/{self.slug}/{store.slug}",
				"missing schedules")
		tasks: list[CoroutineType[Schedule]] = []
		for schedule_id, raw_schedule in schedules.items():
			if not isinstance(raw_schedule, Mapping):
				continue
			if ensure and raw_schedule.get("storeNum") != store.sid:
				continue
			course = courses.get(raw_schedule.get("courseId"))
			if not isinstance(course, Mapping):
				continue
			slug = course.get("urlTitle")
			if not isinstance(slug, str):
				continue
			tasks.append(Schedule.get(root_path = store.root_path, scheduleId = schedule_id,
				slug = slug, remote = remote, session = session))
		results = await AsyncGather(tasks)
		if date:
			results = [schedule for schedule in results
				if schedule.naive_start.date() == date.date()]
		return results

	async def get_courses(self, root_path: str | None = None, fast: bool = False,
		session: SessionType | None = None) -> list[Course]:
		root = self.root_path if root_path is None else root_path
		raw_stores = storeReturn(ROOT_TO_FLAG[root], opening = True)
		stores = [Store(store = store, root_path = root) for store in raw_stores]
		schedules = await self.get_multiple_schedules(stores = stores, fast = fast,
			session = session)
		return sorted({schedule.course for schedule in schedules})

class Sitemap(TodayObject):
	hash_fields: ClassVar[tuple[str, ...]] = ("url_path",)
	sort_fields: ClassVar[tuple[str, ...]] = ("url_path",)

	def __init__(self, root_path: str | None = None, flag: str | None = None) -> None:
		if root_path is None and flag is None:
			raise ValueError("root_path 和 flag 必须提供一个")
		if flag is not None:
			region = Regions.get(flag)
			if region is None or region.url_retail is None:
				raise ValueError(f"未知地区 {flag!r}")
			self.url_path = region.url_retail
		else:
			assert root_path is not None
			self.url_path = root_path.replace("/cn", ".cn")
		self.using = self.match_by_valid if not known_slugs() else self.match_by_assure
		self.runtime = datetime.now()
		self.raw: dict[str, Any] = {"url_path": self.url_path}

	def match_by_assure(self, slug: str) -> bool:
		return slug not in known_slugs()

	def match_by_valid(self, slug: str) -> bool:
		matches = re.findall(DATE_FRAGMENT_PATTERN, slug)
		return bool(matches and date_candidates(matches[0][1], self.runtime))

	def __repr__(self) -> str:
		return f"<Sitemap \"{self.url_path}\">"

	async def read_sitemap(self, text: str, session: SessionType | None,
		seen: set[str], depth: int = 0) -> list[str]:
		if depth > 3:
			return []
		root = ET.fromstring(text)
		if root.tag.endswith("sitemapindex"):
			urls: list[str] = []
			for node in root.iter():
				if not node.tag.endswith("loc") or not node.text:
					continue
				url = node.text.strip()
				if url in seen:
					continue
				seen.add(url)
				try:
					child = await fetch_text(url, session = session)
				except TodayAPIError:
					continue
				urls.extend(await self.read_sitemap(child, session, seen, depth + 1))
			return urls
		return [node.text.strip() for node in root.iter()
			if node.tag.endswith("loc") and node.text and node.text.strip()]

	async def get_urls(self, session: SessionType | None = None) -> list[str]:
		url = f"https://www.apple.com{self.url_path}/today/sitemap.xml"
		text = await fetch_text(url, session = session)
		locations = await self.read_sitemap(text, session, {url})
		slugs: dict[str, list[str]] = {}
		for location in locations:
			parsed = urlparse(location)
			if "/today/event/" not in parsed.path:
				continue
			slug = parsed.path.split("/today/event/", 1)[1].split("/", 1)[0]
			if not slug or not self.using(slug):
				continue
			slugs.setdefault(slug, []).append(location)
		result: list[str] = []
		for slug, urls in slugs.items():
			urls.sort()
			if self.using == self.match_by_valid or self.match_by_valid(slug):
				result.append(urls[1 if len(urls) > 1 else 0])
			else:
				result.append(urls[0])
		return result

	async def get_objects(self, extend_schedule: bool = False,
		session: SessionType | None = None) -> list[Collection | Course | Schedule]:
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		async with get_session(session) as ses:
			urls = await self.get_urls(session = ses)
			results = await AsyncGather(
				(get_url(url, session = ses, semaphore = semaphore) for url in urls),
				return_exceptions = True)
			objects = [result for result in results if not isinstance(result, Exception)]
			if extend_schedule:
				available = {obj.scheduleId for obj in objects if isinstance(obj, Schedule)}
				for obj in list(objects):
					if not isinstance(obj, Course) or not obj.special or obj.courseId in available:
						continue
					try:
						objects.append(await obj.get_single_schedule(session = ses))
					except Exception:
						pass
		return objects

def parse_url(url: str) -> ParsedURL | dict[str, str]:
	"""解析 Today at Apple 的课程、排课或系列 URL。"""
	parsed = urlparse(url)
	host = parsed.netloc.lower()
	if not (host in ("apple.com", "apple.com.cn")
		or host.endswith((".apple.com", ".apple.com.cn"))):
		return {}
	parts = [part for part in parsed.path.split("/") if part]
	try:
		index = parts.index("today")
	except ValueError:
		return {}
	root_path = "/" + "/".join(parts[:index]) if index else ""
	if not root_path and host.endswith(".cn"):
		root_path = "/cn"
	tail = parts[index + 1:]
	if len(tail) < 2 or tail[0] not in ("event", "collection"):
		return {}
	kind, slug = tail[0], tail[1]
	if not slug:
		return {}
	base = "https://www.apple.com.cn" if root_path == "/cn" else "https://www.apple.com"
	prefix = "" if root_path == "/cn" else root_path
	if kind == "collection":
		return {
			"type": "collection", "root_path": root_path, "slug": slug,
			"url": f"{base}{prefix}/today/collection/{slug}"}
	schedule_id = tail[2] if len(tail) > 2 and tail[2].isdigit() else ""
	sid = (parse_qs(parsed.query).get("sn") or [""])[0]
	if schedule_id:
		sn = f"?sn={sid}" if sid else ""
		return {
			"type": "schedule", "root_path": root_path, "slug": slug,
			"scheduleId": schedule_id, "sid": sid,
			"url": f"{base}{prefix}/today/event/{slug}/{schedule_id}/{sn}"}
	return {
		"type": "course", "root_path": root_path, "slug": slug,
		"url": f"{base}{prefix}/today/event/{slug}"}

async def generate_graph(stores: list[Store], graph: dict[str, list[str]] | None = None,
	retry: int = 3, limit: int = 10) -> dict[str, list[str]]:
	graph = {} if graph is None else graph
	while retry and stores:
		retry -= 1
		await AsyncGather((store.get_covering_stores(graph) for store in stores),
			limit = limit, return_exceptions = True)
		stores = [store for store in stores if store.sid not in graph]
	for store in stores:
		graph[store.sid] = []
	payload = json.dumps(graph, ensure_ascii = False, indent = 2, sort_keys = True)
	await asyncio.to_thread(Path("Retail/taa-graph.json").write_text, payload)
	return graph

async def get_url(url: str,
	session: SessionType | None = None,
	semaphore: SemaphoreType | None = None) -> Collection | Course | Schedule:
	info = parse_url(url)
	match info:
		case {"type": "schedule", "root_path": root, "slug": slug, "scheduleId": schedule_id}:
			return await Schedule.get(root_path = root, scheduleId = schedule_id,
				slug = slug, session = session)
		case {"type": "course", "root_path": root, "slug": slug}:
			return await Course.get(root_path = root, slug = slug, session = session)
		case {"type": "collection", "root_path": root, "slug": slug}:
			return await Collection.get(root_path = root, slug = slug, session = session)
		case _:
			raise ValueError(f"不支持 Today at Apple URL: {url!r}")
