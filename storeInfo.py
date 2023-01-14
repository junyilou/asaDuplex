import json
import re
from datetime import datetime
from functools import total_ordering
from modules.constants import allRegions, userAgent
from modules.util import request
from typing import Any, Optional

STORES: dict[str, "Store"] = {}
DEFAULTFILE = "storeInfo.json"

@total_ordering
class Store:
	def __init__(self, sid: int | str, dct: dict):
		for e in ["name", "flag", "state", "city"]:
			assert e in dct, f"key {e} not exist"

		self.sid: str = f"{sid:0>3}"
		self.rid: str = f"R{self.sid}"
		self.iid: int = int(self.sid)
		self.flag: str = dct["flag"]

		self.name: str = dct["name"]
		self.altname: list[str]
		if isinstance(self.name, list):
			self.altname = self.name
			self.name = self.altname.pop(0)
		else:
			self.altname = []

		if "timezone" in dct:
			self.timezone: str = dct["timezone"]

		self.nso: str
		self.dates: list[str]
		if "dates" in dct:
			self.dates = self.nso = dct["dates"]
			if isinstance(self.nso, list):
				self.nso = self.nso[0]
			else:
				self.dates = [self.dates]

		if "modified" in dct:
			self.modified: str = dct["modified"]

		self.isClosed: bool
		self.isFuture: bool
		self.isIntern: bool
		if "status" in dct:
			self.isClosed = dct["status"] == "closed"
			self.isFuture = dct["status"] == "future"
			self.isIntern = dct["status"] == "internal"
		else:
			self.isClosed = self.isFuture = self.isIntern = False
		self.isNormal: bool = not any([self.isClosed, self.isFuture, self.isIntern])

		self.state: str = dct["state"]
		self.city: str = dct["city"]
		self.region: dict = allRegions[self.flag]
		if "website" in dct:
			self.slug: str = self.name.lower().replace(" ", "") if dct["website"] == "-" else dct["website"]
			self.url: str = f"https://www.apple.com{self.region['storeURL']}/retail/{self.slug}"

		self.keys: list[str] = list(filter(None, [
			*dct.get("alter", "").split(" "),
			self.name, self.state, self.city, self.flag,
			*self.altname,
			getattr(self, "slug", ""),
			self.region["name"], self.region["nameEng"], self.region["abbr"],
			*self.region["altername"],
			*(["招聘", "Hiring"] if self.isFuture else []),
			*(["关闭", "Closed"] if self.isClosed else []),
			*(["内部", "Internal"] if self.isIntern else [])]))
		self.keys += [k.replace(" ", "") for k in self.keys if " " in k]

		self.sortkey: tuple[str, str, str] = (self.flag, self.state, self.sid)
		self.raw: dict = dct

	def telename(self, bold: bool = False, flag: bool = False, sid: bool = True) -> str:
		c = ((flag, f"{self.flag} "), (bold, "*"), (True, f"Apple {self.name}"), (bold, "*"), (sid, f" ({self.rid})"))
		return "".join([j for i, j in c if i])

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

	def __repr__(self):
		name = [f"<Store {self.telename(flag = True)}>"]
		status = [f"({s[2:].capitalize()})" for s in ["isClosed", "isFuture", "isIntern"] if getattr(self, s)]
		return " ".join(name + status)

	def __gt__(self, other):
		if type(other) is not type(self):
			return NotImplemented
		return self.sortkey > other.sortkey

	def __eq__(self, other):
		if type(other) is not type(self):
			return NotImplemented
		return self.sortkey == other.sortkey

	def __hash__(self):
		return hash(self.sortkey)

	async def detail(self, session = None, mode: str = "dict") -> Optional[str | dict[str, Any]]:
		try:
			assert hasattr(self, "slug")
			url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={self.slug}&locale={self.region['rspLocale']}&sc=false"
			if mode == "url":
				return url

			r: dict[str, Any] = await request(session = session, url = url, headers = userAgent,
				ensureAns = False, retryNum = 3, timeout = 5, mode = "json")
			hours = {"isnso": r["hours"]["isNSO"], "regular": r["hours"]["hoursData"], "special": r["hours"]["specialHoursData"]}

			match mode:
				case "raw":
					return r
				case "hours":
					return hours
				case "dict":
					add = r["address"]
					address = ", ".join([a.strip() for a in filter(None, [add["address1"], add["address2"]])])
					province = ", ".join([a.strip() for a in filter(None, [add["city"], add["stateName"], add["postal"]])])
					info = {"timezone": r["timezone"], "telephone": r["telephone"], "address": address, "province": province}
					return r["geolocation"] | info | hours
		except:
			return {}

	@property
	def dieter(self) -> str:
		args = "crop=1"
		'''
			Akamai Image Server Refrence:
			https://developer.goacoustic.com/acoustic-content/docs/how-to-optimize-and-transform-your-images-automatically-with-akamai-1
		'''
		return f"https://rtlimages.apple.com/cmc/dieter/store/16_9/{self.rid}.png?{args}"

	async def header(self, session = None) -> Optional[str]:
		try:
			r: dict[str, Any] = await request(session = session, url = self.dieter, headers = userAgent, ssl = False,
				method = "HEAD", allow_redirects = False, raise_for_status = True, mode = "head", timeout = 5)
			return r['Last-Modified'][5:-4]
		except:
			return None

def StoreID(sid: int | str, fuzzy: bool = False) -> list[Store]:
	try:
		assert sid
		if fuzzy:
			sid = str(sid).upper().removeprefix("R")
			assert sid.isdigit()
			stores = [i for i in STORES.values() if sid in i.sid]
		else:
			sid = f"{str(sid).upper().removeprefix('R'):0>3}"
			assert sid.isdigit()
			stores = [STORES[sid]] if sid in STORES else []
	except AssertionError:
		return []
	return stores

def StoreMatch(keyword: str, fuzzy: bool = False) -> list[Store]:
	if not keyword:
		return []
	if keyword == "all" and fuzzy:
		return list(STORES.values())
	if fuzzy:
		stores = [i for i in STORES.values() if any([keyword.lower() in k.lower() for k in i.keys])]
	else:
		stores = [i for i in STORES.values() if keyword.lower() in [k.lower() for k in i.keys]]
	return stores

def getStore(sid: int | str) -> Optional[Store]:
	f = f"{str(sid).upper().removeprefix('R'):0>3}"
	return STORES.get(f, None)

def nameReplace(rstores: list[Store], bold: bool = False, number: bool = True,
	final: str = "name", userLang: Optional[list[bool | None]] = [None]) -> list[str]:
	if not rstores:
		return []
	stores = set(rstores)
	levels = ["flag", "state", "city"]
	results = []
	boldmark = "*" if bold else ""
	userLang = [userLang] if not isinstance(userLang, list) else userLang

	for store in stores:
		for level in levels:
			ast = set([s for s in STORES.values() if getattr(s, level) == getattr(store, level) and s.isNormal])
			if ast and ast.issubset(stores):
				stores = stores.symmetric_difference(ast)
				if level == "flag":
					attrs = {None: store.flag, True: store.region["name"], False: store.region["nameEng"]}
					attr = " ".join([attrs[i] for i in userLang])
				else:
					attr = getattr(store, level)
				num = f" ({len(ast)})" if number else ""
				results.append((f"{boldmark}{attr}{boldmark}{num}", level))
	results = [s[0] for s in sorted(results, key = lambda k: (levels.index(k[1]), k[0]))]
	results += [getattr(s, final) for s in stores]
	return results

def reloadJSON(filename: str = DEFAULTFILE) -> str:
	global STORES
	with open(filename) as r:
		infoJSON = json.load(r)
	STORES = {sid: Store(sid = sid, dct = dct) for sid, dct in infoJSON.items() if sid != "update"}
	STORES = {k: v for k, v in sorted(STORES.items(), key = lambda s: s[1])}
	return infoJSON["update"]

def storeReturn(args: str | list[str], *, remove_closed: bool = False, remove_future: bool = False,
	fuzzy: bool = False, split: bool = False, sort: bool = True) -> list[Store]:
	ans = []
	match args, split:
		case str(), True:
			args = re.split(",|，", args)
		case list(), False:
			pass
		case _, _:
			args = [args]

	for a in map(lambda s: str(s).strip(), args):
		for stores in (StoreID(a, fuzzy = fuzzy), StoreMatch(a, fuzzy = fuzzy)):
			for s in stores:
				try:
					assert s not in ans
					assert not remove_closed or not s.isClosed and not s.isIntern
					assert not remove_future or not s.isFuture and not s.isIntern
				except AssertionError:
					continue
				ans.append(s)
	if sort:
		ans.sort()
	return ans

reloadJSON()