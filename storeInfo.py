import re
import json
from datetime import datetime
from functools import total_ordering
from modules.constants import allRegions, userAgent
from modules.util import request

STORES = {}
DEFAULTFILE = "storeInfo.json"

@total_ordering
class Store:
	def __init__(self, sid, dct):
		for e in ["name", "flag", "state", "city"]:
			assert e in dct

		self.sid = f"{sid:0>3}"
		self.rid = f"R{sid}"
		self.iid = int(sid)
		self.flag = dct["flag"]

		self.name = dct["name"]
		if isinstance(self.name, list):
			self.altname = self.name
			self.name = self.altname.pop(0)
		else:
			self.altname = []

		if "timezone" in dct:
			self.timezone = dct["timezone"]

		if "dates" in dct:
			self.dates = self.nso = dct["dates"]
			if isinstance(self.nso, list):
				self.nso = self.nso[0]
			else:
				self.dates = [self.dates]

		if "modified" in dct:
			self.modified = dct["modified"]

		if "status" in dct:
			self.isFuture = dct["status"] == "future"
			self.isClosed = dct["status"] == "closed"
			self.isIntern = dct["status"] == "internal"
		else:
			self.isFuture = self.isClosed = self.isIntern = False

		self.state = dct["state"]
		self.city = dct["city"]
		self.region = allRegions[self.flag]
		if "website" in dct:
			self.slug = self.name.lower().replace(" ", "") if dct["website"] == "-" else dct["website"]
			self.url = f"https://www.apple.com{self.region['storeURL']}/retail/{self.slug}"
		
		self.keys = ((dct["alter"].split(" ") if "alter" in dct else []) + 
			[self.name, self.state, self.city, self.flag] + self.altname + 
			([self.slug] if hasattr(self, "slug") else []) + 
			[self.region["name"], self.region["nameEng"], self.region["abbr"]] + self.region["altername"] + 
			(["招聘", "Hiring"] if self.isFuture else []) + 
			(["关闭", "Closed"] if self.isClosed else []))
		self.keys += [k.replace(" ", "") for k in self.keys if " " in k]

		self.sortkey = f"{self.flag} {self.state} {self.sid}"
		self.raw = dct

	def telename(self, bold = False, flag = False, sid = True):
		bold = "*" if bold else ""
		flag = f"{self.flag} " if flag else ""
		sid = f" ({self.rid})" if sid else ""
		return f"{flag}{bold}Apple {self.name}{bold}{sid}"

	def nsoString(self, userLang = True):
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
		return f"<Store {self.telename(flag = True)}>"

	def __ge__(self, other):
		assert isinstance(other, Store)
		return self.sortkey >= other.sortkey

	def __hash__(self):
		return hash(self.sid)

	async def detail(self, session = None, mode = "dict"):
		try:
			assert hasattr(self, "slug")
			url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={self.slug}&locale={self.region['rspLocale']}&sc=false"
			if mode == "url":
				return url

			r = await request(session = session, url = url, headers = userAgent, 
				ensureAns = False, retryNum = 3, timeout = 5, mode = "json")

			hours = {
				"isnso": r["hours"]["isNSO"],
				"regular": r["hours"]["hoursData"],
				"special": r["hours"]["specialHoursData"]}

			match mode:
				case "raw":
					return r
				case "hours":
					return hours
				case "dict":
					add = r["address"]
					address = add["address1"].rstrip(" ")
					address += f', {add["address2"]}' if add["address2"] else ""
					prov = add["city"]
					prov += f', {add["stateName"]}' if add["stateName"] else ""
					prov += f', {add["postal"]}' if add["postal"] else ""
					info = {
						"timezone": r["timezone"],
						"telephone": r["telephone"],
						"address": address,
						"province": prov
					}
					return r["geolocation"] | info | hours
		except:
			return {}

	@property
	def dieter(self):
		args = "crop=1"
		'''
			Akamai Image Server Refrence: 
			https://developer.goacoustic.com/acoustic-content/docs/how-to-optimize-and-transform-your-images-automatically-with-akamai-1
		'''
		return f"https://rtlimages.apple.com/cmc/dieter/store/16_9/{self.rid}.png?{args}"

	async def header(self, session = None):
		try:
			r = await request(session = session, url = self.dieter, headers = userAgent, ssl = False,
				method = "HEAD", allow_redirects = False, raise_for_status = True, mode = "head", timeout = 5)
			return r['Last-Modified'][5:-4]
		except:
			return None

def StoreID(sid: int | str, fuzzy = False) -> list[Store]:
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

def StoreMatch(keyword: str, fuzzy = False) -> list[Store]:
	if not keyword:
		return []
	if keyword == "all" and fuzzy:
		return list(STORES.values())
	if fuzzy:
		stores = [i for i in STORES.values() if any([keyword.lower() in k.lower() for k in i.keys])]
	else:
		stores = [i for i in STORES.values() if keyword.lower() in [k.lower() for k in i.keys]]
	return stores

def nameReplace(rstores: [Store], bold = False, number = True, final = "name", userLang = [None]) -> list[str]:
	if not rstores:
		return rstores
	stores = set(rstores)
	levels = ["flag", "state", "city"]
	results = []
	bold = "*" if bold else ""
	userLang = [userLang] if not isinstance(userLang, list) else userLang
	
	for store in stores:
		for level in levels:
			ast = set([s for s in STORES.values() if getattr(s, level) == getattr(store, level) and 
				not (s.isClosed or s.isFuture or s.isIntern)])
			if ast and ast.issubset(stores):
				stores = stores.symmetric_difference(ast)
				if level == "flag":
					attrs = {None: store.flag, True: store.region["name"], False: store.region["nameEng"]}
					attr = " ".join([attrs[i] for i in userLang])
				else:
					attr = getattr(store, level)
				num = f" ({len(ast)})" if number else ""
				results.append((f"{bold}{attr}{bold}{num}", level))
	results = [s[0] for s in sorted(results, key = lambda k: (levels.index(k[1]), k[0]))]
	results += [getattr(s, final) for s in stores]
	return results

def storeReturn(args: str | list, remove_closed = False, remove_future = False, 
	fuzzy = False, split = False, sort = True) -> list[Store]:
	ans = []
	if split:
		args = re.split(",|，", args)
	if type(args) in [int, str]:
		args = [f"{args}"]
	for a in args:
		a = a.strip()
		stores = StoreID(str(a), fuzzy = fuzzy) + StoreMatch(str(a), fuzzy = fuzzy)
		for s in stores:
			if remove_closed and (s.isClosed or s.isIntern):
				continue
			if remove_future and (s.isFuture or s.isIntern):
				continue
			if s not in ans:
				ans.append(s)
	if sort:
		ans.sort(key = lambda k: k.sortkey)
	return ans

def reloadJSON(filename = DEFAULTFILE) -> str:
	global STORES
	with open(filename) as r:
		infoJSON = json.load(r)
	for sid, dct in infoJSON.items():
		if sid == "update":
			continue
		STORES[sid] = Store(sid = sid, dct = dct)
	STORES = {k: v for k, v in sorted(STORES.items(), key = lambda s: s[1].sortkey)}
	return infoJSON["update"]

def getStore(sid: int | str) -> Store:
	f = f"{str(sid).upper().removeprefix('R'):0>3}"
	return STORES[f] if f in STORES else None

reloadJSON()