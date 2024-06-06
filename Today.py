import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Optional

from modules.today import (Collection, Course, Schedule, Sitemap, Store,
                           teleinfo)
from modules.util import AsyncGather, get_session, setLogger, sortOD
from storeInfo import storeReturn

DEFAULT_FLAGS = "🇨🇳", "🇭🇰", "🇲🇴", "🇹🇼", "🇯🇵"

async def post(text: str, image: str, keyboard: list[list[list[str]]]) -> Optional[dict]:
	from bot import chat_ids
	from botpost import async_post
	push = {"mode": "photo-text", "text": text, "image": image,
		"parse": "MARK", "chat_id": chat_ids[0], "keyboard": keyboard}
	return await async_post(push)

async def entry(saved: dict[str, Any], mode: str, flags: Sequence[str]) -> None:
	append = False
	courses: dict[Course, set[Schedule]] = {}
	results: list[Collection | Course | Schedule] = []

	async with get_session() as session:
		match mode:
			case "today":
				stores = storeReturn(flags, opening = True)
				tasks = [Store(store = store).getSchedules(session = session) for store in stores]
			case "sitemap":
				tasks = [Sitemap(flag = flag).getObjects(session = session) for flag in flags]
			case _:
				return
		runners = await AsyncGather(tasks, return_exceptions = True)
	runners, exp = [[i for i in runners if b ^ isinstance(i, Exception)] for b in (True, False)]
	for e in exp:
		assert isinstance(e, Exception)
		logging.error(repr(e))
	r = {i for j in runners if isinstance(j, list) for i in j}
	course_collection, schedule = [[i for i in r if b ^ isinstance(i, Schedule)] for b in (True, False)]
	results = sorted(course_collection, key = lambda v: v.rootPath) + sorted(schedule)

	for j in results:
		match j:
			case Schedule(course = c):
				courses.setdefault(c, set()).add(j)
			case Course() as c:
				courses.setdefault(c, set())

	for course in courses:
		doSend = False
		conditions: tuple[bool, bool, bool] = (len(courses[course]) > 0, course.courseId in saved["today"],
			course.flag in saved["sitemap"].get(course.courseId, {}).get("names", {}))

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
				saved["today"][course.courseId] = {"slug": course.slug, "names": {course.flag: course.name}}
			case False, False, False:
				append = True
				if course.courseId not in saved["sitemap"]:
					doSend = True
					saved["sitemap"][course.courseId] = {"slug": course.slug, "names": {}}
				saved["sitemap"][course.courseId]["names"][course.flag] = course.name
		if conditions[0] and course.courseId in saved["sitemap"]:
			append = doSend = True
			del saved["sitemap"][course.courseId]

		if doSend:
			logging.info(str(course))
			schedules = [i for j in (courses[c] for c in courses if c.courseId == course.courseId) for i in j]
			text, image, keyboard = teleinfo(course = course, schedules = schedules, prior = flags)
			await post(text, image, keyboard)

	if append:
		logging.info("正在更新 savedEvent 文件")
		saved["update"] = f"{datetime.now():%F %T}"
		with open("Retail/savedEvent.json", "w") as w:
			json.dump(sortOD(saved, reverse = [True, False]), w, ensure_ascii = False, indent = 2)

async def main(args: Namespace) -> None:
	setLogger(logging.INFO, __file__, base_name = True, force_print = args.debug)
	logging.info("程序启动")
	with open("Retail/savedEvent.json") as r:
		saved = json.load(r)
	await entry(saved, "sitemap" if args.sitemap else "today", args.flags)
	logging.info("程序结束")

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("flags", metavar = "FLAG", type = str, nargs = "*", help = "指定国家或地区旗帜", default = DEFAULT_FLAGS)
	parser.add_argument("-d", "--debug", action = "store_true", help = "打印调试信息")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	parser.add_argument("-s", "--sitemap", action = "store_true", help = "网站地图模式")
	args = parser.parse_args()
	asyncio.run(main(args))