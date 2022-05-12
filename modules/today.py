import re
import json
import asyncio
import pytz
import atexit

from datetime import datetime
from storeInfo import *
from modules.constants import request, webNation, userAgent, sync, disMarkdown, timezoneText, todayNation

__session_pool = {}

API_ROOT = "https://www.apple.com/today-bff/"

API = {
	"landing": API_ROOT + "landing/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}",
	"session": {
		"course": API_ROOT + "session/course?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}",
		"schedule": API_ROOT + "session/schedule?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}&scheduleId={SCHEDULEID}",
		"store": API_ROOT + "session/course/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&courseSlug={COURSESLUG}"
	},
	"collection": {
		"geo": API_ROOT + "collection/geo?stageRootPath={ROOTPATH}&collectionSlug={COLLECTIONSLUG}",
		"store": API_ROOT + "collection/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&collectionSlug={COLLECTIONSLUG}"
	}
}

TIMEOUT = 5
RETRYNUM = 5

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
def __clean(loop = None):
	try:
		l = [asyncio.get_running_loop()] if loop == None else [loop]
	except:
		l = [i for i in __session_pool]
	
	async def __clean_task(loop):
		await __session_pool[loop].close()

	for loop in l:
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
				slug = storeURL(storeid = self.sid, mode = "slug")
				self.rootPath = {**webNation, "🇨🇳": "/cn"}[sif["flag"]]
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
			self.rootPath = {**webNation, "🇨🇳": "/cn"}[sif["flag"]]
			self.timezone = sif["timezone"]
			self.timezoneFlag = False
			self.flag = sif["flag"]
			self.url = storeURL(sif = sif)
		else:
			raise ValueError("sid, raw 至少提供一个")
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

	async def getCourses(self):

		r = await request(
			session = get_session(),
			url = API["landing"].format(STORESLUG = self.slug, ROOTPATH = self.rootPath),
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

	async def getSchedules(self):

		r = await request(
			session = get_session(),
			url = API["landing"].format(STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM, headers = userAgent)
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = raw["schedules"][i], 
				rootPath = self.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = raw["schedules"][i]["storeNum"],
					raw = raw["stores"][raw["schedules"][i]["storeNum"]] if \
						raw["schedules"][i]["storeNum"] in raw["stores"] else None,
					rootPath = self.rootPath), 
				course = await getCourse(
					courseId = raw["schedules"][i]["courseId"], 
					raw = raw["courses"][raw["schedules"][i]["courseId"]], 
					rootPath = self.rootPath,
					moreAbout = [m for m in raw["heroGallery"] if m["heroType"] == "TAG"],
					fuzzy = False)
				) for i in raw["schedules"] if (raw["schedules"][i]["storeNum"] == self.sid)
					 or ("VIRTUAL" in raw["courses"][raw["schedules"][i]["courseId"]]["type"])
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
			self.courseId = courseId
			self.name = raw["name"]
			self.title = raw["title"]
			self.slug = raw["urlTitle"]

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
							self.collection = await getCollection(rootPath = self.rootPath, slug = moreDict["collId"], identifier = self.courseId)
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

	def elements(self, accept = ["jpg", "png", "mp4", "mov"]):
		accept = "|".join(accept)
		result = []
		none = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + accept + 
			"))+[\'\"]?", self.json()) if i[0] not in result]
		return result

	async def getSchedules(self, store):

		r = await request(
			session = get_session(),
			url = API["session"]["store"].format(STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = raw["schedules"][i], 
				rootPath = store.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = raw["schedules"][i]["storeNum"], 
					raw = raw["stores"][raw["schedules"][i]["storeNum"]],
					rootPath = store.rootPath), 
				course = await getCourse(
					raw = raw["courses"][self.courseId], 
					courseId = self.courseId, 
					rootPath = store.rootPath,
					moreAbout = raw["moreAbout"],
					fuzzy = False),
				) for i in raw["schedules"] if 
					(raw["schedules"][i]["courseId"] == self.courseId) and 
					((raw["schedules"][i]["storeNum"] == store.sid) or 
					("VIRTUAL" in raw["courses"][self.courseId]["type"]))
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getRootSchedules(self):
		stores = storeReturn(todayNation.get(self.rootPath, ""), remove_closed = True, remove_future = True)
		tasks = [self.getSchedules(getStore(sid = i[0])) for i in stores]
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
				self.scheduleId = scheduleId
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
		self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/collection/{self.slug}/"

		r = await request(
			session = get_session(),
			url = API["collection"]["geo"].format(COLLECTIONSLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)

		try:
			raw = json.loads(_separate(r))
			self.name = raw["name"]
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取系列 {self.rootPath}/{self.slug} 数据失败") from None

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
		return f'<Collection {self.name}, "{self.slug}", "{self.rootPath}">'

	def __hash__(self):
		return hash(f"{self.rootPath}/{self.slug}")

	def __eq__(self, other):
		try:
			return self.__hash__ == other.__hash__
		except:
			return False

	def json(self):
		return json.dumps(self.raw, ensure_ascii = False)

	def elements(self, accept = ["jpg", "png", "mp4", "mov"]):
		accept = "|".join(accept)
		result = []
		none = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + accept + 
			"))+[\'\"]?", self.json()) if i[0] not in result]
		return result

	async def getSchedules(self, store):

		r = await request(
			session = get_session(),
			url = API["collection"]["store"].format(STORESLUG = store.slug, COLLECTIONSLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = TIMEOUT, retryNum = RETRYNUM)
		
		try:
			raw = json.loads(_separate(r))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {store.rootPath}/{self.slug}/{store.slug} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = raw["schedules"][i], 
				rootPath = store.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = raw["schedules"][i]["storeNum"],
					raw = raw["stores"][raw["schedules"][i]["storeNum"]] if \
						raw["schedules"][i]["storeNum"] in raw["stores"] else None,
					rootPath = store.rootPath), 
				course = await getCourse(
					raw = raw["courses"][raw["schedules"][i]["courseId"]], 
					courseId = raw["schedules"][i]["courseId"], 
					rootPath = store.rootPath,
					moreAbout = self,
					fuzzy = False)
				) for i in raw["schedules"] if 
					raw["courses"][raw["schedules"][i]["courseId"]]["collectionName"] == self.name
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getRootSchedules(self):
		stores = storeReturn(todayNation.get(self.rootPath, ""), remove_closed = True, remove_future = True)
		tasks = [self.getSchedules(getStore(sid = i[0])) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

async def getCollection(slug, rootPath = None, identifier = 0):
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
		matches = re.findall(r"/event/([0-9A-Za-z\-]*-([0-9]{6}))", i)
		if matches and validDates(matches[0][1], runtime, False) != []:
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
	collectionPattern = r"([\S]*apple\.com([\/\.a-zA-Z]*)/today/collection/([a-z0-9\-]*))(/\S*)"
	
	course = re.findall(coursePattern, url, re.I)
	schedule = re.findall(schedulePattern, url, re.I)
	collection = re.findall(collectionPattern, url, re.I)

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
				"rootPath": course[0][1].replace(".cn", "/cn"),
				"slug": course[0][2],
				"url": f"https://www.apple.com{collection[0][1]}/today/collection/{collection[0][2]}"
			}
	else:
		parse = None
	return parse

def validDates(ex, runtime, process = True):
	v = []
	for pattern in ["%y%m%d", "%d%m%y", "%m%d%y"]:
		try:
			date = datetime.strptime(ex, pattern).date()
		except ValueError:
			pass
		else:
			delta = abs(date.year - runtime.year)
			if delta > 1:
				continue
			delta = (date - runtime.date()).days
			if delta > -7:
				v.append(date)
	if process:
		return " (或) ".join([i.strftime("%Y 年 %-m 月 %-d 日") for i in v])
	else:
		return v

def teleinfo(course = None, schedules = None, collection = None, mode = "new"):
	runtime = datetime.now()
	offset = runtime.astimezone().utcoffset().total_seconds() / 3600

	if collection != None:
		if collection.collaboration != None:
			collab = []
			try:
				for i in collection.collaboration:
					collab.append(f"{i['name']}\n{i['description']}")
				collab = "\n\n*合作机构*\n" + "\n\n".join(collab)
			except:
				collab = ""
		else:
			collab = ""

		text = disMarkdown(f"""#TodayatApple {'新' if mode == "new" else ''}系列\n
*{collection.name}*\n
*系列简介*
{collection.description['long']}{collab}""")

		image = collection.images["landscape"]
		keyboard = [[["了解系列", collection.url]]]

		return text, image, keyboard

	if course.virtual:
		courseStore = "线上活动"
	elif schedules != []:
		availableStore = []
		for schedule in schedules:
			if schedule.store.sid[1:] not in availableStore:
				availableStore.append(schedule.store.sid[1:])
		textStore = stateReplace(availableStore)
		for a in textStore:
			if a.isdigit():
				textStore[textStore.index(a)] = actualName(storeInfo(a)["name"])
		courseStore = "、".join(textStore)
	else:
		courseStore = "Apple Store 零售店"

	specialPrefix = (f"{course.collection.name} 系列活动\n" if hasattr(course.collection, "slug") else
		f"{course.collection} 系列活动\n") if course.collection != None else ""

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
		
		if len(schedules) > 1:
			timing = f"{schedule.datetimeStart()} – {schedule.datetimeEnd()}{tzText} 起，共 {len(schedules)} 次排课"
		else:
			timing = f"{schedule.datetimeStart()} – {schedule.datetimeEnd()}{tzText}"
		keyboard = [[["预约课程", schedule.url]]]
	else:
		try:
			date = re.findall(r"[0-9]{6}", course.slug)[-1]
			valid = validDates(date, runtime)
		except IndexError:
			valid = ""
		timing = "尚无可确定的课程时间" if valid == "" else valid
		keyboard = [[["了解课程", course.url]]]

	keyboard[0].append(["下载配图", course.images["landscape"]])

	if schedules != []:
		rsvp = [i.status for i in schedules]
		upCount = rsvp.count(True)
		seCount = len(schedules)
		if seCount > 1:
			if upCount:
				signing = "所有场次均可预约" if upCount == seCount else f"{seCount} 场中的 {upCount} 场可预约"
			else:
				signing = "所有场次均不可预约"
		else:
			signing = "本场活动可预约" if upCount else "本场活动不可预约"
		signingPrefix = "*截止发稿时…*\n" if mode == "new" else "*可预约状态*\n"
	else:
		signing = signingPrefix = ""

	text = disMarkdown(f"""#TodayatApple {'新' if mode == "new" else ''}活动\n
{specialPrefix}*{course.name}*\n
🗺️ {courseStore}
🕘 {timing}\n
*课程简介*
{course.description['long']}\n
{signingPrefix}{signing}""")

	image = course.images["landscape"]

	return text, image, keyboard