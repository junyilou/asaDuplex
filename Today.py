import asyncio
import json
import logging
from datetime import datetime
from sys import argv
from typing import Optional

from modules.today import Collection, Course, Schedule, Sitemap, Store, teleinfo
from modules.util import get_session, setLogger, sortOD
from storeInfo import storeReturn

TODAYARGS = ["🇨🇳", "🇭🇰", "🇲🇴", "🇹🇼", "🇯🇵"]

async def post(text: str, image: str, keyboard: list[list[list[str]]]) -> Optional[dict]:
	from bot import chat_ids
	from botpost import async_post
	push = {"mode": "photo-text", "text": text, "image": image,
		"parse": "MARK", "chat_id": chat_ids[0], "keyboard": keyboard}
	return await async_post(push)

async def main(mode: str) -> None:
	append = False
	courses: dict[Course, set[Schedule]] = {}
	results: list[Collection | Course | Schedule] = []

	async with get_session() as session:
		match mode:
			case "today":
				stores = storeReturn(TODAYARGS, opening = True)
				tasks = [Store(store = store).getSchedules(session = session) for store in stores]
			case "sitemap":
				tasks = [Sitemap(flag = flag).getObjects(session = session) for flag in TODAYARGS]
			case _:
				return
		runners = await asyncio.gather(*tasks, return_exceptions = True)
	runners, exp = [[i for i in runners if b ^ isinstance(i, BaseException)] for b in [True, False]]
	for e in exp:
		assert isinstance(e, BaseException)
		logging.error(repr(e))
	r = {i for j in runners if isinstance(j, list) for i in j}
	course_collection, schedule = [[i for i in r if b ^ isinstance(i, Schedule)] for b in [True, False]]
	results = sorted(course_collection, key = lambda v: v.rootPath) + sorted(schedule)

	for j in results:
		match j:
			case Schedule(course = c):
				courses.setdefault(c, set()).add(j)
			case Course() as c:
				courses.setdefault(c, set())

	for course in courses:
		doSend, toSave = False, {"slug": course.slug, "names": {course.flag: course.name}}
		conditions: tuple[bool, bool, bool] = (
			len(courses[course]) > 0,
			course.courseId in saved["today"],
			course.courseId in saved["sitemap"])

		if isinstance(course.collection, Collection):
			collection = course.collection
			if collection.slug in saved["collection"]:
				if course.flag not in saved["collection"][collection.slug]:
					saved["collection"][collection.slug][collection.flag] = collection.name
			else:
				append = True
				saved["collection"][collection.slug] = {collection.flag: collection.name}
				logging.info(str(collection))
				text, image, keyboard = teleinfo(collection = collection)
				await post(text, image, keyboard)

		match conditions:
			case True, True, _:
				if course.flag not in saved["today"][course.courseId]["names"]:
					append = True
					saved["today"][course.courseId]["names"][course.flag] = course.name
			case True, False, _:
				append = doSend = True
				saved["today"][course.courseId] = toSave
			case False, False, False:
				append = doSend = True
				saved["sitemap"][course.courseId] = toSave
		match conditions:
			case True, _, True:
				del saved["sitemap"][course.courseId]["names"][course.flag]
				append = doSend = True
				if not saved["sitemap"][course.courseId]["names"]:
					del saved["sitemap"][course.courseId]

		if doSend:
			logging.info(str(course))
			schedules = [i for j in (courses[c] for c in courses if c.courseId == course.courseId) for i in j]
			text, image, keyboard = teleinfo(course = course, schedules = schedules, prior = TODAYARGS)
			await post(text, image, keyboard)

	if append:
		logging.info("正在更新 savedEvent 文件")
		saved["update"] = f"{datetime.now():%F %T}"
		with open("Retail/savedEvent.json", "w") as w:
			json.dump(sortOD(saved, reverse = [True, False]), w, ensure_ascii = False, indent = 2)

setLogger(logging.INFO, __file__, base_name = True)
logging.info("程序启动")
argv[1:] = argv[1:] or ["today"]
with open("Retail/savedEvent.json") as m:
	saved = json.loads(m.read())
asyncio.run(main(argv[1]))
logging.info("程序结束")