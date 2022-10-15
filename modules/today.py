import re
import json
import asyncio
import aiohttp
import pytz
import atexit

from datetime import datetime
from storeInfo import *
from modules.constants import allRegions, userAgent
from modules.util import request, disMarkdown, timezoneText

__session_pool = {}

TIMEOUT, RETRYNUM, SEMAPHORE_LIMIT = 5, 5, 50
API_ROOT = "https://www.apple.com/today-bff/"
VALIDDATES = r"([0-9A-Za-z\-]*-([0-9]{6,8}))"
ACCEPT = ["jpg", "png", "mp4", "mov", "pages", "key", "pdf"]
todayNation = dict([(allRegions[i]["rootPath"], i) for i in allRegions if i != "TW"])

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

savedToday = {"Store": {}, "Course": {}, "Schedule": {}, "Collection": {}}

def set_session(session):
	loop = asyncio.get_running_loop()
	__session_pool[loop] = session

def get_session():
	loop = asyncio.get_running_loop()
	session = __session_pool.get(loop, None)
	if session is None:
		session = aiohttp.ClientSession(loop = loop, headers = userAgent)
		__session_pool[loop] = session
	return session

@atexit.register
def clean(loop = None):
	try:
		l = [asyncio.get_running_loop()] if loop == None else [loop]
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

def _separate(text):
	for i in ["\u200B", "\u200C", "\u2060"]:
		text = text.replace(i, "")
	for i in ["\u00A0"]:
		text = text.replace(i, " ")
	return text

def resolution(vids, direction = None):
	res = {}
	for v in vids:
		f = re.findall(r"([0-9]+)x([0-9]+)\.[a-zA-Z0-9]+", v)
		if not f:
			return vids[-1]
		res[v] = [int(f[0][0]), int(f[0][1])]
	vids.sort(key = lambda k: res[k][0] * res[k][1], reverse = True)
	
	if not direction:
		return vids[0]
	else:
		if direction == "p":
			fil = [i for i in vids if res[i][0] < res[i][1]]
		elif direction == "l":
			fil = [i for i in vids if res[i][0] > res[i][1]]
		return fil[0] if fil else None

def validDates(ex, runtime):
	v = []
	if len(ex) == 6:
		possible = ["%y%m%d", "%d%m%y", "%m%d%y"]
	elif len(ex) == 8:
		possible = ["%Y%m%d", "%d%m%Y", "%m%d%Y"]
	else:
		possible = []
	for pattern in possible:
		try:
			date = datetime.strptime(ex, pattern).date()
		except ValueError:
			pass
		else:
			delta = abs(date.year - runtime.year)
			if delta > 1:
				continue
			delta = (date - runtime.date()).days
			if delta > -7 and date not in v:
				v.append(date)
	return v

class asyncObject(object):
	async def __new__(cls, *args, **kwargs):
		instance = super().__new__(cls)
		await instance.__init__(*args, **kwargs)
		return instance

	async def __init__(self):
		pass

class Store():
	def __init__(self, raw = None, sid = None, rootPath = None):

		if raw != None:
			self.name = raw["name"]
			self.sid = raw["storeNum"]
			self.timezone = raw["timezone"]["name"]
			self.timezoneFlag = True
			self.slug = raw["slug"]
			if rootPath == None:
				sif = storeInfo(self.sid)
				slug = storeURL(sid = self.sid, mode = "slug")
				self.rootPath = allRegions[sif["flag"]]["rootPath"]
			else:
				self.rootPath = rootPath
			self.flag = todayNation[self.rootPath]
			self.url = f"https://www.apple.com{'.cn' if self.rootPath == '/cn' else ''}{raw['path']}"
		elif sid != None:
			store = StoreID(sid)[0]
			self.sid = "R" + store[0]
			self.name = store[1]
			sif = storeInfo(self.sid)
			self.slug = storeURL(sif = sif, mode = "slug")
			self.rootPath = allRegions[sif["flag"]]["rootPath"]
			self.timezone = sif["timezone"]
			self.timezoneFlag = False
			self.flag = sif["flag"]
			self.url = storeURL(sif = sif)
		else:
			raise ValueError("sid, raw 至少提供一个")
		self.today = self.url.replace("/retail/", "/today/")
		self.calendar = self.url.replace("/retail/", "/today/calendar/")
		self.serial = dict(sid = self.sid)
		self.raw = dict((i, self.__dict__[i]) for i in self.__dict__ if i != "raw")

	def __hash__(self):
		return hash(self.sid)

	def __eq__(self, other):
		try:
			return self.sid == other.sid
		except:
			return False

	def __repr__(self):
		return f'<Store "{self.name}" ({self.sid}), "{self.slug}", "{self.rootPath}">'

	async def getCourses(self, ensure = True):

		r = await request(
			session = get_session(),
			url = (API["landing"]["store"] if ensure else API["landing"]["nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM, headers = userAgent)
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = [
			getCourse(
				courseId = i, 
				raw = raw["courses"][i], 
				rootPath = self.rootPath, 
				moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
				fuzzy = False
			) for i in raw["courses"]]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getSchedules(self, ensure = True):

		r = await request(
			session = get_session(),
			url = (API["landing"]["store"] if ensure else API["landing"]["nearby"]).format(
				STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM, headers = userAgent)
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = schedules[i], 
				rootPath = self.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = storeNum, 
					rootPath = self.rootPath,
					raw = raw["stores"][storeNum] if storeNum in raw["stores"] else None),
				course = await getCourse(
					courseId = schedules[i]["courseId"], 
					raw = raw["courses"][schedules[i]["courseId"]], 
					rootPath = self.rootPath,
					moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
					fuzzy = False)
				) for i in (raw["schedules"]) if (
					((schedules := raw["schedules"]) != {}) and 
					((not ensure) or ((storeNum := schedules[i]["storeNum"]) == self.sid) or 
					("VIRTUAL" in raw["courses"][raw["schedules"][i]["courseId"]]["type"]))
				)
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

def getStore(sid, raw = None, rootPath = None):
	global savedToday
	if sid in savedToday["Store"]:
		if raw != None:
			get = Store(raw = raw, rootPath = rootPath)
			savedToday["Store"][sid] = get
	else:
		get = Store(sid = sid, raw = raw, rootPath = rootPath)
		savedToday["Store"][sid] = get
	return savedToday["Store"][sid]

class Course(asyncObject):
	async def __init__(self, courseId = None, raw = None, rootPath = None, slug = None, moreAbout = None):
		
		if raw == None:
			if not all([slug, rootPath != None]):
				raise ValueError("slug, rootPath 必须全部提供")
			else:
				self.slug = slug
				self.rootPath = rootPath

			r = await request(
				session = get_session(),
				url = API["session"]["course"].format(COURSESLUG = self.slug, ROOTPATH = self.rootPath),
				ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)

			try:
				raw = json.loads(_separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课程 {rootPath}/{self.slug} 数据失败") from None

			courseId = [i for i in raw["courses"] if raw["courses"][i]["urlTitle"] == slug][0]
			moreAbout = raw["moreAbout"]
			raw = raw["courses"][courseId]

		if all([courseId, raw, rootPath != None]):
			self.rootPath = rootPath
			self.flag = todayNation[self.rootPath]
			self.courseId = courseId
			self.name = raw["name"].strip()
			self.title = raw["title"]
			self.slug = raw["urlTitle"]
			self.serial = dict(slug = self.slug, rootPath = self.rootPath)

			self.collection = None
			if moreAbout != None:
				if type(moreAbout) == Collection:
					self.collection = moreAbout
				elif type(moreAbout) == dict:
					moreAbout = [moreAbout]
				if type(moreAbout) == list:
					for moreDict in moreAbout:
						try:
							if "title" in moreDict and raw["collectionName"] == moreDict["title"]:
								pass
							elif "name" in moreDict and raw["collectionName"] == moreDict["name"]:
								pass
							else:
								continue
							self.collection = await getCollection(rootPath = self.rootPath, slug = moreDict["collId"])
							break
						except:
							pass
			if self.collection == None:
				self.collection = raw["collectionName"]

			self.description = {
				"long": raw["longDescription"].strip(),
				"medium": raw["mediumDescription"].strip(),
				"short": raw["shortDescription"].strip()
			}

			if raw["modalVideo"]:
				self.intro = {
					"poster": raw["modalVideo"]["poster"]["source"],
					"video": resolution(raw["modalVideo"]["sources"]),
				}
			else:
				self.intro = {}

			media = raw["backgroundMedia"]
			self.images = {
				"portrait": media["images"][0]["portrait"]["source"],
				"landscape": media["images"][0]["landscape"]["source"]
			}
			if "ambientVideo" in media:
				self.videos = {
					"portrait": {
						"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
						"video": resolution(media["ambientVideo"]["sources"], "p"),
					},
					"landscape": {
						"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
						"video": resolution(media["ambientVideo"]["sources"], "l"),
					}
				}
			else:
				self.videos = {}

			self.virtual = "VIRTUAL" in raw["type"]
			self.special = "SPECIAL" in raw["type"] or "HIGH" in raw["talentType"]
			self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}"
			self.raw = raw

	def __repr__(self):
		col = (f', Collection <{self.collection.name}>' if type(self.collection) == Collection \
			else f', Collection "{self.collection}"') if self.collection != None else ""
		return f'<Course {self.courseId} "{self.name}", "{self.slug}"{col}>'

	def __hash__(self):
		return hash(f"{self.rootPath}/{self.courseId}")

	def __eq__(self, other):
		try:
			return self.courseId == other.courseId and self.rootPath == other.rootPath
		except:
			return False

	def __lt__(self, other):
		if self.courseId == other.courseId:
			return self.rootPath < other.rootPath
		else:
			return self.courseId < other.courseId

	def __gt__(self, other):
		if self.courseId == other.courseId:
			return self.rootPath > other.rootPath
		else:
			return self.courseId > other.courseId

	def json(self):
		return json.dumps(self.raw, ensure_ascii = False)

	def elements(self, accept = None):
		if accept == None:
			accept = ACCEPT
		
		result, accept = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + accept + 
			"))+[\'\"]?", self.json()) if i[0] not in result]
		return result

	async def getSchedules(self, store, ensure = True, semaphore = None):

		if semaphore != None:
			await semaphore.acquire()
		r = await request(
			session = get_session(),
			url = (API["session"]["store"] if ensure else API["session"]["nearby"]).format(
				STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)
		if semaphore != None:
			semaphore.release()
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = schedules[i], 
				rootPath = store.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = storeNum, 
					raw = raw["stores"][storeNum],
					rootPath = store.rootPath), 
				course = await getCourse(
					raw = raw["courses"][self.courseId], 
					courseId = self.courseId, 
					rootPath = store.rootPath,
					moreAbout = raw["moreAbout"],
					fuzzy = False),
				) for i in raw["schedules"] if (
					((schedules := raw["schedules"]) != {}) and
					((schedules[i]["courseId"] == self.courseId) and 
					(((storeNum := schedules[i]["storeNum"]) == store.sid) or 
					("VIRTUAL" in raw["courses"][self.courseId]["type"]) or (not ensure)))
				)
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getRootSchedules(self):
		stores = storeReturn(todayNation.get(self.rootPath, ""), remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		tasks = [self.getSchedules(getStore(sid = i[0]), semaphore = semaphore) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

async def getCourse(courseId, rootPath = None, raw = None, moreAbout = None, fuzzy = True):
	global savedToday
	saved = list(savedToday["Course"])
	if rootPath == "":
		rootPath = "/us"
	if not fuzzy:
		if rootPath == None:
			raise ValueError("在非模糊模式下 rootPath 必须提供")
		keyword = f"{rootPath}/{courseId}"
	else:
		keyword = f"{courseId}"
	for i in saved:
		if keyword in i:
			return savedToday["Course"][i]
	
	if rootPath == None:
		raise ValueError("没有找到匹配，需要提供 rootPath")

	get = await Course(raw = raw, courseId = courseId, rootPath = rootPath.replace("/us", ""), moreAbout = moreAbout)
	savedToday["Course"][f"{rootPath}/{courseId}"] = get
	return get

class Schedule(asyncObject):
	async def __init__(self, scheduleId = None, raw = None, rootPath = None, slug = None, store = None, course = None):

		if raw == None:
			if not all([slug, scheduleId, rootPath != None]):
				raise ValueError("slug, scheduleId, rootPath 必须全部提供")
			else:
				self.slug = slug
				self.scheduleId = scheduleId = f"{scheduleId}"
				self.rootPath = rootPath

			r = await request(
				session = get_session(),
				url = API["session"]["schedule"].format(COURSESLUG = self.slug, SCHEDULEID = self.scheduleId, ROOTPATH = self.rootPath),
				ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)

			try:
				raw = json.loads(_separate(r))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课次 {self.rootPath}/{self.slug}/{self.scheduleId} 数据失败") from None

			store = getStore(
				sid = raw["schedules"][scheduleId]["storeNum"],
				raw = raw["stores"][raw["schedules"][scheduleId]["storeNum"]], 
				rootPath = self.rootPath)
			course = await getCourse(
				raw = raw["courses"][raw["schedules"][scheduleId]["courseId"]], 
				courseId = raw["schedules"][scheduleId]["courseId"], 
				rootPath = self.rootPath,
				moreAbout = raw["moreAbout"],
				fuzzy = False)
			raw = raw["schedules"][scheduleId]

		if all([scheduleId, raw, rootPath != None, course, store]):
			self.__dict__ = course.__dict__.copy()
			self.course = course
			self.scheduleId = scheduleId
			self.rootPath = rootPath
			self.flag = todayNation[self.rootPath]
			self.serial = dict(slug = self.slug, scheduleId = self.scheduleId, rootPath = self.rootPath)

			self.store = store
			self.timezone = store.timezone
			try:
				self.tzinfo = pytz.timezone(self.timezone)
				self.timeStart = datetime.fromtimestamp(raw["startTime"] / 1000, self.tzinfo)
				self.timeEnd = datetime.fromtimestamp(raw["endTime"] / 1000, self.tzinfo)
			except:
				self.tzinfo = self.timeStart = self.timeEnd = None
			self.rawStart = datetime.fromtimestamp(raw["startTime"] / 1000)
			self.rawEnd = datetime.fromtimestamp(raw["endTime"] / 1000)
			self.status = raw["status"] == "RSVP"
			self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}/{self.scheduleId}/?sn={self.store.sid}"
			self.raw = raw

	def datetimeStart(self, form = "%-m 月 %-d 日 %-H:%M"):
		if self.tzinfo != None:
			return self.timeStart.astimezone(self.tzinfo).strftime(form)
		return self.rawStart.strftime(form)

	def datetimeEnd(self, form = "%-H:%M"):
		if self.tzinfo != None:
			return self.timeEnd.astimezone(self.tzinfo).strftime(form)
		return self.rawEnd.strftime(form)

	def json(self):
		return json.dumps(self.raw, ensure_ascii = False)

	def __repr__(self):
		loc = self.store.sid if not self.course.virtual else "Online"
		return f'<Schedule {self.scheduleId} of {self.course.courseId}, {self.datetimeStart("%-m/%-d %-H:%M")}-{self.datetimeEnd()} @ {loc}>'

	def __hash__(self):
		return hash(self.scheduleId)

	def __eq__(self, other):
		try:
			return self.scheduleId == other.scheduleId
		except:
			return False

	def __lt__(self, other):
		if self.rawStart == other.rawStart:
			return self.scheduleId < other.scheduleId
		else:
			return self.rawStart < other.rawStart

	def __gt__(self, other):
		if self.rawStart == other.rawStart:
			return self.scheduleId > other.scheduleId
		else:
			return self.rawStart > other.rawStart

async def getSchedule(scheduleId, raw = None, rootPath = None, slug = None, store = None, course = None):
	global savedToday
	scheduleId = f"{scheduleId}"
	if any([raw, rootPath, slug]):
		get = await Schedule(scheduleId = scheduleId, raw = raw, rootPath = rootPath, slug = slug, store = store, course = course)
		savedToday["Schedule"][scheduleId] = get
	return savedToday["Schedule"][scheduleId]

class Collection(asyncObject):
	async def __init__(self, rootPath = None, slug = None):
		
		if not all([rootPath != None, slug]):
			raise ValueError("slug, rootPath 必须全部提供")

		self.slug = slug
		self.rootPath = rootPath
		self.flag = todayNation[self.rootPath]
		self.url = f"https://www.apple.com{rootPath.replace('/cn', '.cn')}/today/collection/{slug}/"
		self.serial = dict(slug = slug, rootPath = rootPath)

		r = await request(
			session = get_session(),
			url = API["collection"]["geo"].format(COLLECTIONSLUG = slug, ROOTPATH = rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)

		try:
			raw = json.loads(_separate(r))
			self.name = raw["name"].strip()
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取系列 {rootPath}/{slug} 数据失败") from None

		self.description = {
			"long": raw["longDescription"].strip(),
			"medium": raw["mediumDescription"].strip(),
			"short": raw["shortDescription"].strip()
		}

		media = raw["heroGallery"][0]["backgroundMedia"]
		self.images = {
			"portrait": media["images"][0]["portrait"]["source"],
			"landscape": media["images"][0]["landscape"]["source"]
		}
		if "ambientVideo" in media:
			self.videos = {
				"portrait": {
					"poster": media["ambientVideo"]["poster"][0]["portrait"]["source"],
					"video": resolution(media["ambientVideo"]["sources"], "p"),
				},
				"landscape": {
					"poster": media["ambientVideo"]["poster"][0]["landscape"]["source"],
					"video": resolution(media["ambientVideo"]["sources"], "l"),
				}
			}
		else:
			self.videos = {}

		if "inCollaborationWith" in raw:
			self.collaboration = raw["inCollaborationWith"]["partners"]
		else:
			self.collaboration = None
		self.raw = raw

	def __repr__(self):
		return f'<Collection "{self.name}", "{self.slug}", "{self.rootPath}">'

	def __hash__(self):
		return hash(f"{self.rootPath}/{self.slug}")

	def __eq__(self, other):
		try:
			return self.__hash__() == other.__hash__()
		except:
			return False

	def json(self):
		return json.dumps(self.raw, ensure_ascii = False)

	def elements(self, accept = None):
		if accept == None:
			accept = ACCEPT
		
		result, accept = [], "|".join(accept)
		_ = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + accept + 
			"))+[\'\"]?", self.json()) if i[0] not in result]
		return result

	async def getSchedules(self, store, ensure = True, semaphore = None):

		if semaphore != None:
			await semaphore.acquire()
		r = await request(
			session = get_session(),
			url = (API["collection"]["store"] if ensure else API["collection"]["nearby"]).format(
				STORESLUG = store.slug, COLLECTIONSLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)
		if semaphore != None:
			semaphore.release()
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = schedules[i], 
				rootPath = store.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = storeNum,
					raw = raw["stores"][storeNum] if storeNum in raw["stores"] else None,
					rootPath = store.rootPath), 
				course = await getCourse(
					raw = raw["courses"][courseId], 
					courseId = courseId, 
					rootPath = store.rootPath,
					moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
					fuzzy = False)
				) for i in raw["schedules"] if 
					((schedules := raw["schedules"]) != {}) and (courseId := schedules[i]["courseId"]) and 
					((self.slug in [m["collId"] for m in raw["heroGallery"] if m["heroType"] == "TAG"]) and 
					(((storeNum := schedules[i]["storeNum"]) == store.sid) or (not ensure) or
					("VIRTUAL" in raw["courses"][courseId]["type"])))
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getRootSchedules(self):
		stores = storeReturn(todayNation.get(self.rootPath, ""), remove_closed = True, remove_future = True)
		semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
		tasks = [self.getSchedules(getStore(sid = i[0]), semaphore = semaphore) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

async def getCollection(slug, rootPath = None):
	global savedToday
	saved = list(savedToday["Collection"])
	if rootPath == None:
		raise ValueError("slug, rootPath 必须全部提供")
	keyword = f"{rootPath}/{slug}"
	for i in saved:
		if keyword == i:
			return savedToday["Collection"][i]
	
	get = await Collection(rootPath = rootPath, slug = slug)
	savedToday["Collection"][keyword] = get
	return get

async def Sitemap(rootPath):
	runtime = datetime.now()
	r = await request(
		session = get_session(), 
		url = f"https://www.apple.com{rootPath}/today/sitemap.xml",
		ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM, headers = userAgent)
	urls = re.findall(r"<loc>\s*(\S*)\s*</loc>", r)

	slugs = {}
	for i in urls:
		matches = re.findall(f"/event/{VALIDDATES}", i)
		if matches and validDates(matches[0][1], runtime) != []:
			slugs[matches[0][0]] = slugs.get(matches[0][0], []) + [i]

	tasks = [
		parseURL(
			url = sorted(slugs[i], reverse = True)[0], 
			coro = True) for i in slugs
		]
	return await asyncio.gather(*tasks, return_exceptions = True)

def parseURL(url, coro = False):
	coursePattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*))"
	schedulePattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([a-z0-9\-]*)/(6[0-9]{18})(\/\?sn\=([R0-9]{4}))?)"
	collectionPattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/collection/([a-z0-9\-]*))(/\S*)?"
	
	course = re.findall(coursePattern, url, re.I)
	schedule = re.findall(schedulePattern, url, re.I)
	collection = re.findall(collectionPattern, url, re.I)

	async def nothing():
		return None

	if schedule:
		if coro:
			parse = getSchedule(slug = schedule[0][2], scheduleId = schedule[0][3], rootPath = schedule[0][1].replace(".cn", "/cn"))
		else:
			parse = {
				"type": "schedule",
				"rootPath": schedule[0][1].replace(".cn", "/cn"),
				"slug": schedule[0][2],
				"scheduleId": schedule[0][3],
				"sid": schedule[0][5],
				"url": f"https://www.apple.com{schedule[0][1]}/today/event/{schedule[0][2]}/{schedule[0][3]}/?sn=R{schedule[0][5]}"
			}
	elif course:
		if coro:
			parse = Course(slug = course[0][2], rootPath = course[0][1].replace(".cn", "/cn"))
		else:
			parse = {
				"type": "course",
				"rootPath": course[0][1].replace(".cn", "/cn"),
				"slug": course[0][2],
				"url": f"https://www.apple.com{course[0][1]}/today/event/{course[0][2]}"
			}
	elif collection:
		if coro:
			parse = Collection(slug = collection[0][2], rootPath = collection[0][1].replace(".cn", "/cn"))
		else:
			parse = {
				"type": "collection",
				"rootPath": collection[0][1].replace(".cn", "/cn"),
				"slug": collection[0][2],
				"url": f"https://www.apple.com{collection[0][1]}/today/collection/{collection[0][2]}"
			}
	else:
		if coro:
			parse = nothing()
		else:
			parse = None
	return parse

lang = {
	True: {
		"OR": "或",
		"NEW": "新",
		"JOINT": "、",
		"COURSE": "课程",
		"COLLECTION": "系列",
		"VIRTUAL": "线上活动",
		"COLLAB_WITH": "*合作机构*",
		"DOWNLOAD_IMAGE": "下载图片",
		"LEARN_COLLECTION": "了解系列",
		"LEARN_COURSE": "了解课程",
		"INTRO_COLLECTION": "*系列简介*",
		"INTRO_COURSE": "*课程简介*",
		"SIGN_UP": "预约课程",
		"GENERAL_STORE": "Apple Store 零售店",
		"TOO_MANY_STORE": "{COUNT} 家 Apple Store 零售店",
		"IN_COLLECTION": "{NAME} 系列课程\n",
		"START_FROM": "{START} – {END}{TZTEXT}",
		"START_FROM_ALL": "{START} – {END}{TZTEXT} 起，共 {AMOUNT} 次排课",
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
		"VIRTUAL": "Virtual Event",
		"COLLAB_WITH": "*In collaboration with*",
		"LEARN_COLLECTION": "Learn More",
		"DOWNLOAD_IMAGE": "Poster",
		"LEARN_COURSE": "Learn More",
		"INTRO_COLLECTION": "*Description*",
		"INTRO_COURSE": "*Description*",
		"SIGN_UP": "Sign Up",
		"GENERAL_STORE": "Apple Store",
		"TOO_MANY_STORE": "{COUNT} Apple Store{PLURAL}",
		"IN_COLLECTION": "In Collection {NAME}\n",
		"START_FROM": "{START} – {END}{TZTEXT}",
		"START_FROM_ALL": "{AMOUNT} Schedule{PLURAL}, starting {START} – {END}{TZTEXT}",
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

def teleinfo(course = None, schedules = [], collection = None, mode = "new", userLang = True):
	runtime = datetime.now()
	offset = runtime.astimezone().utcoffset().total_seconds() / 3600

	if collection != None:
		text = disMarkdown(lang[userLang]["MAIN1"].format(
			NEW = lang[userLang]["NEW"] if mode == "new" else '',
			TYPE = lang[userLang]["COLLECTION"],
			NAME = collection.name,
			INTROTITLE = lang[userLang]["INTRO_COLLECTION"],
			INTRO = collection.description['long'],
		))
		if collection.collaboration != None:
			collab = []
			for i in collection.collaboration:
				name = disMarkdown(i["name"])
				collab.append(f"[{name}]({i['url']})" if "url" in i else name)
			text += f"\n\n{lang[userLang]['COLLAB_WITH']}\n{lang[userLang]['JOINT'].join(collab)}"

		image = collection.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"
		keyboard = [[[lang[userLang]["LEARN_COLLECTION"], collection.url], [lang[userLang]["DOWNLOAD_IMAGE"], collection.images["landscape"]]]]

		return text, image, keyboard

	if course.virtual:
		courseStore = lang[userLang]["VIRTUAL"]
	elif schedules != []:
		availableStore = []
		for schedule in schedules:
			if schedule.store.sid[1:] not in availableStore:
				availableStore.append(schedule.store.sid[1:])
		availableStore = [i[0] for i in storeReturn(availableStore)]
		textStore = stateReplace(availableStore, userLang = userLang)
		for a in textStore:
			if a.isdigit():
				textStore[textStore.index(a)] = actualName(storeInfo(a)["name"])
		courseStore = lang[userLang]["JOINT"].join(textStore)
		if len(courseStore) > 200:
			courseStore = lang[userLang]["TOO_MANY_STORE"].format(
				COUNT = (lenAvail := len(availableStore)), 
				PLURAL = "s" if lenAvail > 1 else "")
	else:
		courseStore = lang[userLang]["GENERAL_STORE"]

	if course.collection == None:
		specialPrefix = ""
	elif hasattr(course.collection, "slug"):
		specialPrefix = lang[userLang]["IN_COLLECTION"].format(NAME = course.collection.name)
	else:
		specialPrefix = lang[userLang]["IN_COLLECTION"].format(NAME = course.collection)

	schedules.sort()
	if schedules != []:
		schedule = schedules[0]
		scheduleTimezone = schedule.tzinfo
		if scheduleTimezone != None:
			delta = schedule.timeStart.utcoffset().total_seconds() / 3600
			if delta == offset:
				tzText = ""
			else:
				tzText = " " + timezoneText(schedule.timeStart)
		else:
			tzText = ""
		
		if (lenSchedules := len(schedules)) > 1:
			timing = lang[userLang]["START_FROM_ALL"].format(
				START = schedule.datetimeStart(form = lang[userLang]["FORMAT_START"]),
				END = schedule.datetimeEnd(form = lang[userLang]["FORMAT_END"]),
				TZTEXT = tzText, AMOUNT = len(schedules), PLURAL = "s" if lenSchedules > 1 else "")
		else:
			timing = lang[userLang]["START_FROM"].format(
				START = schedule.datetimeStart(form = lang[userLang]["FORMAT_START"]),
				END = schedule.datetimeEnd(form = lang[userLang]["FORMAT_END"]), TZTEXT = tzText)
		keyboard = [[[lang[userLang]["SIGN_UP"], schedule.url]]]
	else:
		try:
			date = re.findall(VALIDDATES, course.slug)[0][1]
			vals = validDates(date, runtime)
			valid = f' {lang[userLang]["OR"]} '.join([i.strftime(lang[userLang]["FORMAT_DATE"]) for i in vals])
		except IndexError:
			valid = ""
		timing = lang[userLang]["GENERAL_TIMING"] if valid == "" else valid
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