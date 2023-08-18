import asyncio
import json
import logging
from datetime import UTC, datetime
from sys import argv
from typing import Any, Optional

from bot import chat_ids
from botpost import async_post as raw_post
from modules.today import Collection, Course, Schedule, Sitemap, Store, teleinfo
from modules.util import setLogger, sortOD
from storeInfo import storeReturn

TODAYARGS = ["🇨🇳", "🇭🇰", "🇲🇴", "🇹🇼"]

def rec(lst: list[Any], rst: list[Any]) -> list[Any]:
	for i in lst:
		match i:
			case list():
				rec(i, rst)
			case Exception():
				logging.error(f"{i!r}")
			case _:
				if i not in rst:
					rst.append(i)
	return rst

async def async_post(text: str, image: str, keyboard: list[list[list[str]]]) -> Optional[dict]:
	push = {
		"mode": "photo-text", "text": text, "image": image,
		"parse": "MARK", "chat_id": chat_ids[0], "keyboard": keyboard}
	return await raw_post(push)

async def main(mode: str) -> bool:
	append = False
	match mode:
		case "today":
			stores = storeReturn(TODAYARGS, remove_closed = True, remove_future = True)
			tasks = [Store(store = store).getSchedules() for store in stores]
		case "sitemap":
			tasks = [Sitemap(flag = flag).getObjects() for flag in TODAYARGS]
		case _:
			return append

	courses: dict[Course, list[Schedule]] = {}
	results: list[Course | Schedule] = rec(await asyncio.gather(*tasks, return_exceptions = True), [])

	for j in results:
		match j:
			case Schedule(course = c):
				courses[c] = courses.get(c, [])
				if j not in courses[c]:
					courses[c].append(j)
			case Course() as c:
				courses[c] = courses.get(c, [])

	for course in courses:
		doSend, toSave = False, {"slug": course.slug, "names": {course.flag: course.name}}
		conditions: tuple[bool, bool, bool] = (len(courses[course]) > 0, *(course.courseId in saved[s] for s in ("today", "sitemap")))

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
				await async_post(text, image, keyboard)

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
			await async_post(text, image, keyboard)

	return append

setLogger(logging.INFO, __file__, base_name = True)
logging.info("程序启动")

argv[1:] = argv[1:] or ["today"]
with open("Retail/savedEvent.json") as m:
	saved = json.loads(m.read())

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
append = loop.run_until_complete(main(argv[1]))

if append:
	logging.info("正在更新 savedEvent 文件")
	saved["update"] = datetime.now(UTC).strftime("%F %T GMT")
	with open("Retail/savedEvent.json", "w") as w:
		json.dump(sortOD(saved, reverse = [True, False]), w, ensure_ascii = False, indent = 2)

logging.info("程序结束")