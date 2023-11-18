import json
import re
from datetime import datetime
from modules.constants import Regions, userAgent
from modules.util import SessionType, request
from typing import Any, Callable, Literal, Optional, Required, TypedDict

DEFAULTFILE = "storeInfo.json"

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

STORES: dict[str, "Store"] = {}

class Store:
	def __init__(self, sid: int | str, dct: StoreDict) -> None:
		self.sid = f"{sid:0>3}"
		self.rid = "R" + self.sid
		self.iid = int(self.sid)
		self.flag = dct["flag"]

		name = dct["name"]
		if isinstance(name, list):
			self.altname: list[str] = name.copy()
			self.name: str = self.altname.pop(0)
		else:
			self.altname: list[str] = []
			self.name: str = name

		if "dates" in dct:
			raw_dates = dct["dates"]
			if isinstance(raw_dates, list):
				self.dates: list[str] = raw_dates
				self.nso: str = raw_dates[0]
			else:
				self.dates: list[str] = [raw_dates]
				self.nso: str = raw_dates

		if "timezone" in dct:
			self.timezone = dct["timezone"]
		if "modified" in dct:
			self.modified = dct["modified"]

		status = dct.get("status")
		trans_table = {"closed": "关闭", "future": "招聘", "internal": "内部"}
		self.isClosed = status == "closed"
		self.isFuture = status == "future"
		self.isIntern = status == "internal"
		self.isNormal = not (self.isClosed or self.isFuture or self.isIntern)

		self.state = dct["state"]
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
		self.keys += [k.replace(" ", "") for k in self.keys if " " in k]

		self.sortkey = (self.flag, self.state, self.sid)
		self.raw: dict[str, Any] = dict(dct)

	@property
	def dieter(self) -> str:
		args = "crop=1" # https://developer.goacoustic.com/acoustic-content/docs/how-to-optimize-and-transform-your-images-automatically-with-akamai-1
		return f"https://rtlimages.apple.com/cmc/dieter/store/16_9/{self.rid}.png?{args}"

	def __repr__(self) -> str:
		name = [f"Store {self.telename(flag = True)}"]
		status = [f"({s[2:].capitalize()})" for s in ["isClosed", "isFuture", "isIntern"] if getattr(self, s)]
		return f"<{' '.join(name + status)}>"

	def __str__(self) -> str:
		return self.telename(sid = False)

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
		session: Optional[SessionType] = None) -> dict[str, Any]:
		try:
			assert hasattr(self, "detail_url")
			r = await request(session = session, url = self.detail_url, headers = userAgent,
				ensureAns = False, retryNum = 3, timeout = 5, mode = "json")
			if mode == "raw":
				return r
			else:
				hours = {"isnso": r["hours"]["isNSO"], "regular": r["hours"]["hoursData"], "special": r["hours"]["specialHoursData"]}
				if mode == "hours":
					return hours
				add = r["address"]
				address = ", ".join(a.strip() for a in [add["address1"], add["address2"]] if a)
				province = ", ".join(a.strip() for a in [add["city"], add["stateName"], add["postal"]] if a)
				info = {"timezone": r["timezone"], "telephone": r["telephone"], "address": address, "province": province}
				return r["geolocation"] | info | hours
		except:
			return {}

	async def header(self, session: Optional[SessionType] = None) -> Optional[str]:
		try:
			r = await request(session = session, url = self.dieter, headers = userAgent, ssl = False,
				method = "HEAD", allow_redirects = False, raise_for_status = True, mode = "HEAD", timeout = 5)
			return r['Last-Modified'][5:-4]
		except:
			return None

	def nsoString(self, userLang: bool = True) -> str:
		if not hasattr(self, "dates"):
			return ""
		lang = {True: {"OPENED": "首次开幕于 {DATE}", "MOVED": "搬迁换址于 {DATE}", "CLOSED": "结束营业于 {DATE}", "FORMAT": "%Y 年 %-m 月 %-d 日"},
			False: {"OPENED": "Opened on {DATE}", "MOVED": "Moved on {DATE}", "CLOSED": "Closed on {DATE}", "FORMAT": "%b %-d, %Y"}}
		localize = lambda dt, userLang: datetime.strptime(dt, "%Y-%m-%d").strftime(lang[userLang]["FORMAT"])
		info = [lang[userLang]["OPENED"].format(DATE = localize(self.dates[0], userLang))]
		for d in self.dates[1 : -1 if self.isClosed else None]:
			info.append(lang[userLang]["MOVED"].format(DATE = localize(d, userLang)))
		if self.isClosed:
			info.append(lang[userLang]["CLOSED"].format(DATE = localize(self.dates[-1], userLang)))
		return "\n".join(info)

	def telename(self, bold: bool = False, flag: bool = False, sid: bool = True) -> str:
		c = ((flag, f"{self.flag} "), (bold, "*"), (True, f"Apple {self.name}"), (bold, "*"), (sid, f" ({self.rid})"))
		return "".join(j for i, j in c if i)

def StoreID(sid: int | str, fuzzy: Any = False, regular: Any = False) -> list[Store]:
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
	if keyword == "_" and fuzzy:
		return [i for i in STORES.values()]
	if regular:
		pattern = re.compile(keyword, re.I)
		return [i for i in STORES.values() if any(re.search(pattern, k) for k in i.keys)]
	if fuzzy:
		return [i for i in STORES.values() if any(keyword.lower() in k.lower() for k in i.keys)]
	return [i for i in STORES.values() if keyword.lower() in (k.lower() for k in i.keys)]

def getStore(sid: int | str) -> Optional[Store]:
	return STORES.get(sidify(sid), None)

def nameReplace(rstores: list[Store], bold: bool = False, number: bool = True,
	final: str = "name", userLang: Optional[bool | list[Optional[bool]]] = [None]) -> list[str]:
	if not rstores:
		return []
	stores = set(rstores)
	levels = ["flag", "state", "city"]
	results = []
	boldmark = "*" if bold else ""
	userLang = [userLang] if not isinstance(userLang, list) else userLang

	for store in stores:
		for level in levels:
			ast = set(s for s in STORES.values() if getattr(s, level) == getattr(store, level) and s.isNormal)
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
	results += [getattr(s, final) for s in stores]
	return results

def reloadJSON(filename: str = DEFAULTFILE) -> str:
	with open(filename) as r:
		infoJSON = json.load(r)
	update = infoJSON.pop("update", None)
	for sid, dct in infoJSON.items():
		STORES[sid] = Store(sid = sid, dct = dct)
	return update

def sidify(sid: int | str, *, R: bool = False, fill: bool = True) -> str:
	return f"{'R' if R and fill else ''}{str(sid).upper().removeprefix('R'):{'0>3' if fill else ''}}"

def storeReturn(args: Optional[str | list[str]] = None, *, remove_closed: Any = False, remove_future: Any = False,
	fuzzy: Any = False, regular: Any = False, split: Any = False, sort: Any = True, filter: Optional[Callable] = None) -> list[Store]:
	if not args or args == "_":
		args, fuzzy = "_", True
	if not isinstance(args, list):
		args = re.split(r"\s*[,，]\s*", str(args)) if split else [str(args).strip()]
	gen = set(g for s in args for m in (StoreID(s, fuzzy = fuzzy, regular = regular),
		StoreMatch(s, fuzzy = fuzzy, regular = regular)) for g in m)
	ans = [s for s in gen if (not remove_closed or not s.isClosed and not s.isIntern) and
		(not remove_future or not s.isFuture and not s.isIntern)]
	if filter:
		ans = [i for i in ans if filter(i)]
	if sort:
		ans.sort()
	return ans

reloadJSON()