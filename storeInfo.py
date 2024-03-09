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
	alter: str
	city: Required[str]
	dates: str | list[str]
	flag: Required[str]
	modified: str
	name: Required[str | list[str]]
	state: Required[str]
	status: str
	timezone: str
	website: str

class SortKey(Enum):
	default = ""
	id = "id"
	index = "index"

STORES: dict[str, "Store"] = {}

class Store:
	def __init__(self, sid: int | str, dct: StoreDict) -> None:
		self.sid = f"{sid:0>3}"
		assert len(self.sid) == 3, "Invalid Store ID"
		self.rid = f"R{self.sid}"
		self.iid = int(self.sid)
		assert "flag" in dct, 'Key "flag" missed'
		self.flag = dct["flag"]

		assert "name" in dct, 'Key "name" missed'
		name = dct["name"]
		if isinstance(name, list):
			self.altname: list[str] = name.copy()
			self.name: str = self.altname.pop(0)
		else:
			self.altname = []
			self.name = name

		trans_table = {"closed": "关闭", "future": "招聘", "internal": "内部"}
		self.status: str = (dct.get("status") or "").capitalize()
		self.isClosed = self.status == "Closed"
		self.isFuture = self.status == "Future"
		self.isInternal = self.status == "Internal"
		self.isOpen = not (self.isClosed or self.isFuture or self.isInternal)

		if "timezone" in dct:
			self.timezone = dct["timezone"]
		if "dates" in dct:
			assert "timezone" in dct, 'Key "timezone" missed'
			raw_dates = dct["dates"]
			timezone = ZoneInfo(self.timezone)
			if isinstance(raw_dates, list):
				self.dates: list[str] = raw_dates
				self.nso: str = raw_dates[0]
			else:
				self.dates: list[str] = [raw_dates]
				self.nso: str = raw_dates
			self.index = (datetime.strptime(self.nso, "%Y-%m-%d").replace(tzinfo = timezone), self.isInternal, self.sid)
		else:
			self.index = (datetime.max.replace(tzinfo = UTC), self.isInternal, self.sid)
		if "modified" in dct:
			self.modified = dct["modified"]

		assert "state" in dct, 'Key "state" missed'
		self.state = dct["state"]
		assert "city" in dct, 'Key "city" missed'
		self.city = dct["city"]
		self.region = Regions[self.flag]
		if "website" in dct:
			self.slug = dct["website"] or self.name.lower().replace(" ", "")
			self.url = f"https://www.apple.com{self.region.url_retail}/retail/{self.slug}"
			self.detail_url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={self.slug}&locale={self.region.locale}&sc=false"

		keys: list[str] = [
			self.name, self.state, self.city, self.flag, *self.altname,
			*dct.get("alter", "").split(" "),
			getattr(self, "slug", ""),
			self.region.name, self.region.name_eng, self.region.abbr, *self.region.name_alter,
			*([dct["status"].capitalize(), trans_table[dct["status"]]] if "status" in dct else [])]
		self.keys = [i for i in keys if i]
		self.keys.extend(k.replace(" ", "") for k in self.keys if " " in k)

		self.sortkey = (self.flag, self.state, self.city, self.sid)
		self.raw: dict[str, Any] = dict(dct)

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

	async def detail(self,
		mode: Optional[Literal["dict", "hours", "raw"]] = None,
		session: Optional[SessionType] = None,
		raise_exception: bool = False) -> dict[str, Any]:
		try:
			r = await request(self.detail_url, session,
				headers = browser_agent,
				retry = 3, timeout = 5, mode = "json")
			if mode == "raw":
				return r
			else:
				hours = {
					"isnso": r["hours"]["isNSO"],
					"regular": r["hours"]["hoursData"],
					"special": r["hours"]["specialHoursData"]}
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

	def nsoString(self, userLang: bool = True) -> str:
		if not hasattr(self, "dates"):
			return ""
		lang = {True: {"OPENED": "首次开幕于 {}", "REOPEN": "重新开幕于 {}", "CLOSED": "结束营业于 {}", "FORMAT": "%Y 年 %-m 月 %-d 日"},
			False: {"OPENED": "Opened on {}", "REOPEN": "Reopened on {}", "CLOSED": "Closed on {}", "FORMAT": "%b %-d, %Y"}}
		localize = lambda dt, userLang: datetime.strptime(dt, "%Y-%m-%d").strftime(lang[userLang]["FORMAT"])
		info = [lang[userLang]["OPENED"].format(localize(self.dates[0], userLang))]
		for d in self.dates[1 : -1 if self.isClosed else None]:
			info.append(lang[userLang]["REOPEN"].format(localize(d, userLang)))
		if self.isClosed:
			info.append(lang[userLang]["CLOSED"].format(localize(self.dates[-1], userLang)))
		return "\n".join(info)

def StoreID(sid: int | str, fuzzy: Any = False, regular: Any = False) -> list[Store]:
	if sid == "ALL":
		return list(STORES.values())
	try:
		assert sid
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
		infoJSON = json.load(r)
	update = infoJSON.pop("update")
	for sid, dct in infoJSON.items():
		STORES[sid] = Store(sid = sid, dct = dct)
	return update

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
			key = lambda i: i.iid
		case SortKey.index:
			key = lambda i: i.index
	return sorted(answer, key = key)

reloadJSON()