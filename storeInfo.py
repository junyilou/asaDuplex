import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from modules.regions import Regions
from modules.util import SessionType, browser_agent, request
from pathlib import PurePath
from typing import Any, Literal, Optional, Required, TypedDict
from zoneinfo import ZoneInfo

DEFAULTFILE = PurePath(__file__).with_suffix(".json")
type StoreMapping = Callable[[Store], Any]

class StoreDict(TypedDict, total = False):
	city: Required[str]
	dieter: dict[str, str]
	events: dict[str, str]
	flag: Required[str]
	keyword: list[str]
	name: Required[str]
	name_alt: list[str]
	name_eng: str
	nso: str
	slug: str
	state: Required[str]
	status: str
	timezone: str

class FileDict(TypedDict):
	_: str
	stores: dict[str, StoreDict]

class SortKey(Enum):
	default = ""
	id = "id"
	index = "index"

STORES: dict[str, "Store"] = {}

class Store:
	REQUIRED_KEYS = "city", "flag", "name", "state"

	def __init__(self, rid: str, dct: StoreDict) -> None:
		for k in self.REQUIRED_KEYS:
			assert k in dct, f"Key {k!r} is required"

		self.rid = rid
		self.sid = self.rid.removeprefix("R")
		assert len(self.sid) == 3, "Invalid Store ID"

		self.city = dct["city"]
		if "dieter" in dct:
			self.md5 = dct["dieter"]["md5"]
			self.modify = dct["dieter"]["modify"]
		else:
			self.md5 = self.modify = None
		self.events = dct.get("events", {})
		self.flag = dct["flag"]
		self.keyword = dct.get("keyword", [])
		self.name = dct["name"]
		self.name_alt = dct.get("name_alt", [])
		self.name_eng = dct.get("name_eng", self.name)
		self.nso = dct.get("nso")
		self.slug = dct.get("slug")
		self.state = dct["state"]
		self.status = (dct.get("status", "")).capitalize()
		self.timezone = ZoneInfo(dct["timezone"]) if "timezone" in dct else None
		self.raw: dict[str, Any] = dict(dct)

		self.isClosed = self.status == "Closed"
		self.isFuture = self.status == "Future"
		self.isInternal = self.status == "Internal"
		self.isOpen = not any((self.isClosed, self.isFuture, self.isInternal))
		if self.nso and self.timezone:
			self.index = datetime.strptime(self.nso, "%Y-%m-%d %H:%M").replace(tzinfo = self.timezone), self.isInternal, self.sid
		else:
			self.index = datetime.max.replace(tzinfo = UTC), self.isInternal, self.sid
		self.region = Regions[self.flag]
		url = "https://www.apple.com{}/retail/{}"
		self.url = url.format(self.region.url_retail, self.slug) if self.slug else None
		detail_url = "https://www.apple.com/rsp-web/store-detail?storeSlug={}&locale={}&sc=false"
		self.detail_url = detail_url.format(self.slug, self.region.locale) if self.slug else None
		self.sortkey = (self.flag, self.state, self.city, self.sid)

		statuses = {"closed": "关闭", "future": "招聘", "internal": "内部"}
		keys: list[str] = [
			self.name, self.name_eng, self.state, self.city, self.flag,
			*self.name_alt, *self.keyword, (self.nso or "")[:10], self.slug or "",
			self.region.name, self.region.name_eng, self.region.abbr, *self.region.name_alt,
			*((dct["status"].capitalize(), statuses[dct["status"]]) if "status" in dct else ())]
		self.keys = [i for i in keys if i]

	@property
	def dieter(self) -> str:
		args = "crop=1" # https://developer.goacoustic.com/acoustic-content/docs/how-to-optimize-and-transform-your-images-automatically-with-akamai-1
		return f"https://rtlimages.apple.com/cmc/dieter/store/16_9/{self.rid}.png?{args}"

	def __repr__(self) -> str:
		return f"<Store {self:full}{f" ({self.status})" if self.status else ""}>"

	def __str__(self) -> str:
		return format(self)

	def __format__(self, __format_spec: str) -> str:
		presets = {"": "Apple %name",
			"plain": "Apple %name (%rid)",
			"full": "%flag Apple %name (%rid)",
			"telegram": "%flag *Apple %name* (%rid)"}
		temp = "$"
		if temp in __format_spec:
			raise ValueError(f"format spec can not contain {temp!r}")
		spec = presets.get(__format_spec, __format_spec).replace("%%", temp)
		for k in ("sid", "rid", "name", "flag"):
			spec = re.sub(fr"(?<!%)%{k}", getattr(self, k), spec)
		return spec.replace(temp, "%")

	def __lt__(self, other) -> bool:
		if not type(other) is type(self):
			return NotImplemented
		return self.sortkey < other.sortkey

	def __eq__(self, other) -> bool:
		if not type(other) is type(self):
			return NotImplemented
		return self.sortkey == other.sortkey

	def __hash__(self) -> int:
		return hash(self.sortkey)

	def dumps(self) -> dict[str, Any]:
		kept_attrs = "city", "events", "flag", "keyword", "name", "name_alt", "nso", "slug", "state"
		d = {k: v for k in kept_attrs if (v := getattr(self, k)) or k in self.REQUIRED_KEYS}
		if self.md5 and self.modify:
			d["dieter"] = {"md5": self.md5, "modify": self.modify}
		if self.name_eng != self.name:
			d["name_eng"] = self.name_eng
		if self.status:
			d["status"] = self.status.lower()
		if self.timezone:
			d["timezone"] = self.timezone.key
		return d

	async def detail(self,
		mode: Optional[Literal["dict", "hero", "hours", "raw"]] = None,
		session: Optional[SessionType] = None,
		raise_exception: bool = False) -> dict[str, Any]:
		try:
			assert self.detail_url, 'Key "slug" is required'
			r = await request(self.detail_url, session,
				headers = browser_agent,
				retry = 3, timeout = 5, mode = "json")
			if mode == "raw":
				return r
			if mode == "hero":
				return {"hero": r["hero"], "heroImage": r["heroImage"]}
			hours = {"isnso": r["hours"]["isNSO"], "regular": r["hours"]["hoursData"], "special": r["hours"]["specialHoursData"]}
			if mode == "hours":
				return hours
			add = r["address"]
			address = ", ".join(a.strip() for a in [add["address1"], add["address2"]] if a)
			province = ", ".join(a.strip() for a in [add["city"], add["stateName"], add["postal"]] if a)
			info = {"timezone": r["timezone"], "telephone": r["telephone"], "address": address, "province": province}
			return r["geolocation"] | info | hours
		except:
			if raise_exception:
				raise
			return {}

	def events_string(self, userLang: bool = True) -> str:
		events = self.events | ({self.nso: "nso"} if self.nso else {})
		lang = {True: {"nso": "盛大开幕", "rebuild": "焕新开幕", "move": "搬迁地点", "closure": "永久关闭", "_": "%Y 年 %-m 月 %-d 日"},
		  False: {"nso": "Opened", "rebuild": "Rebuild", "move": "Moved", "closure": "Closed", "_": "%b %-d, %Y"}}
		return "\n".join(f"{lang[userLang][v]} {datetime.strptime(k[:10], "%Y-%m-%d"):{lang[userLang]["_"]}}" for k, v in sorted(events.items()))

def StoreID(sid: int | str, fuzzy: Any = False, regular: Any = False) -> list[Store]:
	if sid == "ALL":
		return list(STORES.values())
	try:
		assert sid
		if sid == "XXX":
			return [STORES["XXX"]]
		if regular:
			return [i for i in STORES.values() if re.search(str(sid), i.rid)]
		elif fuzzy:
			sid = sidify(sid, fill = False)
			assert sid.isdigit()
			return [i for i in STORES.values() if sid in i.sid]
		sid = sidify(sid)
		assert sid.isdigit()
		return [STORES[sid]] if sid in STORES else []
	except AssertionError:
		return []

def StoreMatch(keyword: str, fuzzy: Any = False, regular: Any = False) -> list[Store]:
	if not keyword:
		return []
	if keyword == "ALL":
		return list(STORES.values())
	if regular:
		pattern = re.compile(keyword, re.I)
		return [i for i in STORES.values() if any(re.search(pattern, k) for k in i.keys)]
	if fuzzy:
		return [i for i in STORES.values() if any(keyword.lower() in k.lower() for k in i.keys)]
	return [i for i in STORES.values() if keyword.lower() in (k.lower() for k in i.keys)]

def getStore(sid: int | str) -> Optional[Store]:
	return STORES.get(sidify(sid))

def nameReplace(rstores: list[Store], bold: bool = False, number: bool = True,
	final: Callable[[Store], str] = str,
	userLang: Optional[bool | list[Optional[bool]]] = [None]) -> list[str]:
	stores, results = set(rstores), []
	levels = ["flag", "state", "city"]
	boldmark = "*" if bold else ""
	userLang = [userLang] if not isinstance(userLang, list) else userLang

	for store in stores:
		for level in levels:
			ast = {s for s in STORES.values() if getattr(s, level) == getattr(store, level) and s.isOpen}
			if ast and ast.issubset(stores):
				stores = stores.symmetric_difference(ast)
				if level == "flag":
					attrs = {None: store.flag, True: store.region.name, False: store.region.name_eng}
					attr = " ".join(attrs[i] for i in userLang)
				else:
					attr = getattr(store, level)
				num = f" ({len(ast)})" if number else ""
				results.append((f"{boldmark}{attr}{boldmark}{num}", level))
	results = [s[0] for s in sorted(results, key = lambda k: (levels.index(k[1]), k[0]))]
	results.extend(final(s) for s in sorted(stores))
	return results

def reloadJSON(filename: str | PurePath = DEFAULTFILE) -> str:
	with open(filename) as r:
		infoJSON: FileDict = json.load(r)
	for rid, dct in infoJSON["stores"].items():
		inst = Store(rid = rid, dct = dct)
		STORES[inst.sid] = inst
	return infoJSON["_"]

def sidify(sid: int | str, *, R: bool = False, fill: bool = True) -> str:
	return f"{"R" if R and fill else ""}{str(sid).upper().removeprefix("R"):{"0>3" if fill else ""}}"

def storeReturn(args: Any = None, *,
	opening: Any = False,
	remove_closed: Any = False,
	remove_future: Any = False,
	remove_internal: Any = True,
	fuzzy: Any = False,
	regular: Any = False,
	split: Any = False,
	sort: SortKey = SortKey.default,
	filter: Optional[StoreMapping] = None,
	allow_empty: bool = True) -> list[Store]:
	if not args and allow_empty:
		args = "ALL"
	if not isinstance(args, list):
		args = re.split(r"\s*[,，]\s*", str(args)) if split else [args]
	args = [str(a) for a in args]
	gen = {g for s in args for m in (StoreID(s, fuzzy = fuzzy, regular = regular),
		StoreMatch(s, fuzzy = fuzzy, regular = regular)) for g in m}
	filters: list[Optional[StoreMapping]] = [
		lambda i: not opening or i.isOpen,
		lambda i: not remove_closed or not i.isClosed,
		lambda i: not remove_future or not i.isFuture,
		lambda i: not remove_internal or not i.isInternal, filter]
	answer = (i for i in gen if all(f(i) for f in filters if f))
	match sort:
		case SortKey.default:
			key: StoreMapping = lambda i: i
		case SortKey.id:
			key = lambda i: i.sid
		case SortKey.index:
			key = lambda i: i.index
	return sorted(answer, key = key)

reloadJSON()