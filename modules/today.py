import re
import json
import asyncio
import atexit
import pytz

from datetime import datetime
from storeInfo import *
from modules.constants import request, webNation, userAgent, sync, disMarkdown

__session_pool = {}

API_ROOT = "https://www.apple.com/today-bff/"

API = {
	"spotlight": API_ROOT + "spotlight?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}",
	"landing": API_ROOT + "landing/store?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}",
	"session": {
		"course": API_ROOT + "session/course?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}",
		"schedule": API_ROOT + "session/schedule?stageRootPath={ROOTPATH}&courseSlug={COURSESLUG}&scheduleId={SCHEDULEID}",
		"nearby": API_ROOT + "session/course/nearby?stageRootPath={ROOTPATH}&storeSlug={STORESLUG}&courseSlug={COURSESLUG}"
	}
}

savedToday = {"Store": {}, "Course": {}, "Schedule": {}}

def set_session(session):
	loop = asyncio.get_event_loop()
	__session_pool[loop] = session

def get_session():
	loop = asyncio.get_event_loop()
	session = __session_pool.get(loop, None)
	if session is None:
		session = aiohttp.ClientSession(loop = loop, headers = userAgent)
		__session_pool[loop] = session
	return session

def __clean():
	loop = asyncio.get_event_loop()
	async def __clean_task():
		await __session_pool[loop].close()
	if loop.is_closed():
		loop.run_until_complete(__clean_task())
	else:
		loop.create_task(__clean_task())
atexit.register(__clean)

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
			self.locale = raw["locale"]
			self.slug = raw["slug"]
			if rootPath == None:
				sif = storeInfo(self.sid)
				slug = storeURL(storeid = self.sid, mode = "slug")
				self.rootPath = {**webNation, "🇨🇳": "/cn"}[sif["flag"]]
			else:
				self.rootPath = rootPath
			self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}{raw['path']}"
		elif sid != None:
			store = StoreID(sid)[0]
			self.sid = "R" + store[0]
			self.name = store[1]
			sif = storeInfo(self.sid)
			self.slug = storeURL(sif = sif, mode = "slug")
			self.rootPath = {**webNation, "🇨🇳": "/cn"}[sif["flag"]]
			self.timezone = None
			self.locale = None
			self.url = storeURL(sif = sif)
		else:
			raise ValueError("sid, raw 至少提供一个")

	def __hash__(self):
		return hash(self.sid)

	def __eq__(self, other):
		return self.sid == other.sid

	def __repr__(self):
		return f'<Store "{self.name}" ({self.sid}), "{self.slug}", "{self.rootPath}">'

	async def getCourses(self):

		r = await request(
			session = get_session(),
			url = API["landing"].format(STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = 3, retryNum = 3, headers = userAgent)
		
		try:
			raw = json.loads(r.replace("\u2060", "").replace("\u00A0", " "))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = [
			getCourse(
				courseId = i, 
				raw = raw["courses"][i], 
				rootPath = self.rootPath, 
				fuzzy = False
			) for i in raw["courses"]]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getSchedules(self):

		r = await request(
			session = get_session(),
			url = API["landing"].format(STORESLUG = self.slug, ROOTPATH = self.rootPath),
			ensureAns = False, timeout = 3, retryNum = 3, headers = userAgent)
		
		try:
			raw = json.loads(r.replace("\u2060", "").replace("\u00A0", " "))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取 {self.sid} 数据失败") from None

		tasks = [
			getSchedule(
				scheduleId = i, 
				raw = raw["schedules"][i], 
				rootPath = self.rootPath, 
				slug = self.slug, 
				store = getStore(
					sid = self.sid,
					raw = raw["stores"][self.sid],
					rootPath = self.rootPath), 
				course = await getCourse(
					courseId = raw["schedules"][i]["courseId"], 
					raw = raw["courses"][raw["schedules"][i]["courseId"]], 
					rootPath = self.rootPath,
					fuzzy = False)
				) for i in raw["schedules"] if (raw["schedules"][i]["storeNum"] == self.sid)
					 or ("VIRTUAL" in raw["courses"][raw["schedules"][i]["courseId"]]["type"])
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

def getStore(sid, raw = None, rootPath = None):
	global savedToday
	if sid in savedToday["Store"]:
		if raw != None and savedToday["Store"][sid].timezone == None:
			get = Store(raw = raw, rootPath = rootPath)
			savedToday["Store"][sid] = get
	else:
		get = Store(sid = sid, raw = raw, rootPath = rootPath)
		savedToday["Store"][sid] = get
	return savedToday["Store"][sid]

class Course(asyncObject):
	async def __init__(self, courseId = None, raw = None, rootPath = None, slug = None):
		
		if raw == None:
			if not all([slug, rootPath != None]):
				raise ValueError("slug, rootPath 必须全部提供")
			else:
				self.slug = slug
				self.rootPath = rootPath

			r = await request(
				session = get_session(),
				url = API["session"]["course"].format(COURSESLUG = self.slug, ROOTPATH = self.rootPath),
				ensureAns = False, timeout = 3, retryNum = 3)

			try:
				raw = json.loads(r.replace("\u2060", "").replace("\u00A0", " "))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课程 {rootPath}/{self.slug} 数据失败") from None

			courseId = [i for i in raw["courses"] if raw["courses"][i]["urlTitle"] == slug][0]
			raw = raw["courses"][courseId]

		if all([courseId, raw, rootPath != None]):
			self.rootPath = rootPath
			self.courseId = courseId
			self.name = raw["name"]
			self.slug = raw["urlTitle"]
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
		col = f', Collection "{self.collection}"' if self.collection else ""
		return f'<Course {self.courseId} "{self.name}", "{self.slug}"{col}>'

	def __hash__(self):
		return hash(f"{self.rootPath}/{self.courseId}")

	def __eq__(self, other):
		return self.courseId == other.courseId and self.rootPath == other.rootPath

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
			url = API["session"]["nearby"].format(STORESLUG = store.slug, COURSESLUG = self.slug, ROOTPATH = store.rootPath),
			ensureAns = False, timeout = 3, retryNum = 3)
		
		try:
			raw = json.loads(r.replace("\u2060", "").replace("\u00A0", " "))
		except json.decoder.JSONDecodeError:
			raise ValueError(f"获取课次 {self.rootPath}/{self.slug}/{store.slug} 数据失败") from None

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
					fuzzy = False),
				) for i in raw["schedules"] if 
					(raw["schedules"][i]["courseId"] == self.courseId) and 
					((raw["schedules"][i]["storeNum"] == store.sid) or 
					("VIRTUAL" in raw["courses"][self.courseId]["type"]))
			]
		return await asyncio.gather(*tasks, return_exceptions = True)

	async def getRootSchedules(self):
		todayNation = {**{v: k for k, v in webNation.items()}, "/cn": "🇨🇳"}
		stores = storeReturn(todayNation.get(self.rootPath, ""), remove_closed = True, remove_future = True)
		tasks = [self.getSchedules(getStore(sid = i[0])) for i in stores]
		return await asyncio.gather(*tasks, return_exceptions = True)

async def getCourse(courseId, rootPath = None, raw = None, fuzzy = True):
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
	else:
		get = await Course(raw = raw, courseId = courseId, rootPath = rootPath)
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
				ensureAns = False, timeout = 3, retryNum = 3)

			try:
				raw = json.loads(r.replace("\u2060", "").replace("\u00A0", " "))
			except json.decoder.JSONDecodeError:
				raise ValueError(f"获取课次 {rootPath}/{self.slug}/{self.scheduleId} 数据失败") from None

			store = getStore(
				sid = raw["schedules"][scheduleId]["storeNum"],
				raw = raw["stores"][raw["schedules"][scheduleId]["storeNum"]], 
				rootPath = self.rootPath)
			course = await getCourse(
				raw = raw["courses"][raw["schedules"][scheduleId]["courseId"]], 
				courseId = raw["schedules"][scheduleId]["courseId"], 
				rootPath = self.rootPath,
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
				self.rawStart = datetime.fromtimestamp(raw["startTime"] / 1000)
				self.rawEnd = datetime.fromtimestamp(raw["endTime"] / 1000)
			except:
				self.tzinfo = self.rawStart = self.rawEnd = None
				self.timeStart = datetime.fromtimestamp(raw["startTime"] / 1000)
				self.timeEnd = datetime.fromtimestamp(raw["endTime"] / 1000)
			self.status = raw["status"] == "RSVP"
			self.url = f"https://www.apple.com{self.rootPath.replace('/cn', '.cn')}/today/event/{self.slug}/{self.scheduleId}/?sn={self.store.sid}"
			self.raw = raw

	def datetimeStart(self, form = "%-m 月 %-d 日 %-H:%M", tzinfo = None):
		if tzinfo != None:
			return self.timeStart.astimezone(tzinfo).strftime(form)
		return self.timeStart.strftime(form)

	def datetimeEnd(self, form = "%-H:%M", tzinfo = None):
		if tzinfo != None:
			return self.timeEnd.astimezone(tzinfo).strftime(form)
		return self.timeEnd.strftime(form)

	def json(self):
		return json.dumps(self.raw, ensure_ascii = False)

	def __repr__(self):
		loc = self.store.sid if not self.course.virtual else "Online"
		return f'<Schedule {self.scheduleId} of {self.course.courseId}, {self.datetimeStart("%-m/%-d %-H:%M")}-{self.datetimeEnd()} @ {loc}>'

	def __hash__(self):
		return hash(self.scheduleId)

	def __eq__(self, other):
		return self.scheduleId == other.scheduleId

	def __lt__(self, other):
		if self.timeStart == other.timeStart:
			return self.scheduleId < other.scheduleId
		else:
			return self.timeStart < other.timeStart

	def __gt__(self, other):
		if self.timeStart == other.timeStart:
			return self.scheduleId > other.scheduleId
		else:
			return self.timeStart > other.timeStart

async def getSchedule(scheduleId, raw = None, rootPath = None, slug = None, store = None, course = None):
	global savedToday
	scheduleId = f"{scheduleId}"
	if scheduleId not in savedToday["Schedule"]:
		get = await Schedule(scheduleId = scheduleId, raw = raw, rootPath = rootPath, slug = slug, store = store, course = course)
		savedToday["Schedule"][scheduleId] = get
	return savedToday["Schedule"][scheduleId]

class Webpage(asyncObject):
	async def __init__(self, url):
		r = await request(
			session = get_session(), 
			url = url, ensureAns = False, 
			timeout = 3, retryNum = 3, headers = userAgent)
		self.raw = r

	def elements(self, accept = ["jpg", "png", "mp4", "mov"]):
		accept = "|".join(accept)
		result = []
		none = [result.append(i[0]) for i in re.findall(r"[\'\"](http[^\"\']*\.(" + accept + "))+[\'\"]?", self.raw) if i[0] not in result]
		return result

async def Sitemap(rootPath):
	runtime = datetime.now()
	r = await request(
		session = get_session(), 
		url = f"https://www.apple.com{rootPath}/today/sitemap.xml",
		ensureAns = False, timeout = 3, retryNum = 3, headers = userAgent)
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
	coursePattern = r"http[\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([^\/]*)"
	schedulePattern = r"http[\S]*apple\.com([\/\.a-zA-Z]*)/today/event/([^\/]*)/(6[0-9]{18})(\/\?sn\=([R0-9]{4}))?"
	
	course = re.findall(coursePattern, url, re.I)
	schedule = re.findall(schedulePattern, url, re.I)

	if schedule:
		if coro:
			parse = Schedule(slug = schedule[0][1], scheduleId = schedule[0][2], rootPath = schedule[0][0].replace(".cn", "/cn"))
		else:
			parse = {
				"type": "schedule",
				"rootPath": schedule[0][0].replace(".cn", "/cn"),
				"slug": schedule[0][1],
				"scheduleId": schedule[0][2],
				"sid": schedule[0][4]
			}
	elif course:
		if coro:
			parse = Course(slug = course[0][1], rootPath = course[0][0].replace(".cn", "/cn"))
		else:
			parse = {
				"type": "course",
				"rootPath": course[0][0].replace(".cn", "/cn"),
				"slug": course[0][1]
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

def teleinfo(course, schedules, mode = "new"):
	runtime = datetime.now()
	offset = runtime.astimezone().utcoffset().total_seconds() / 3600

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
	specialPrefix = f"{course.collection} 系列活动\n" if course.collection != None else ""

	if schedules != []:
		schedule = schedules[0]
		scheduleTimezone = schedule.tzinfo
		if scheduleTimezone != None:
			delta = schedule.timeStart.utcoffset().total_seconds() / 3600
			if delta == offset:
				tzText = ""
			else:
				dx, dy = str(delta).split(".")
				if dy == "0":
					tzText = f" GMT{int(dx):+}"
				else:
					tzText = f" GMT{int(dx):+}:{60 * float('.' + dy):0>2.0f}"
		else:
			tzText = ""
		
		if len(schedules) > 1:
			timing = f"{schedule.datetimeStart()} – {schedule.datetimeEnd()}{tzText} 起，共 {len(schedules)} 次排课"
			if course.virtual:
				keyboard = [[["预约课程", schedule.url]]]
			else:
				keyboard = [[[f"预约课程 ({schedule.store.name})", schedule.url]]]
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