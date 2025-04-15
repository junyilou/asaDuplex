import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from modules.today import (VALIDDATES, Collection, Course, Peers, Schedule,
                           Sitemap, Store, ValidDates)
from modules.util import (AsyncGather, SessionType, disMarkdown, session_func,
                          setLogger, sortOD, tz_text)
from storeInfo import storeReturn

DEFAULT_FLAGS = ["🇨🇳", "🇭🇰", "🇲🇴", "🇹🇼"]

def generate_collection(collection: Collection) -> tuple[str, str, list[list[list[str]]]]:
	body = [disMarkdown(t) for t in ("#TodayatApple 新系列", f"*{collection.name}*",
		f"*系列简介*\n{collection.description["long"]}")]
	collab = [f"[{disMarkdown(c.name)}]({u})" if (u := c.links.get("URL"))
		else disMarkdown(c.name) for c in collection.talents]
	if collab:
		body.append(f"*合作机构*\n{"、".join(collab)}")
	image = collection.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"
	keyboard = [[["了解系列", collection.url], ["下载图片", collection.images["landscape"]]]]
	return "\n\n".join(body), image, keyboard

def generate_course(course: Course, schedules: list[Schedule] = [],
	prior: list[str] = []) -> tuple[str, str, list[list[list[str]]]]:

	schedules = sorted(s for s in set(schedules) if s.flag in prior)
	store_counter = Counter(s.raw_store for s in schedules)
	flag_counter = Counter(r.flag for r in store_counter)
	flag_result = sorted(flag_counter.items(), key = lambda x: prior.index(x[0]))
	if course.virtual:
		stores_text = "线上活动"
	elif not schedules:
		stores_text = "Apple Store 零售店"
	elif len(store_counter) == 1:
		stores_text = str(schedules[0].raw_store)
	else:
		stores_text = "、".join(f"{flag} ({count} 家)" for flag, count in flag_result)

	match course.collection:
		case None:
			extra_prefix = ""
		case Collection() as c:
			extra_prefix = f"{c.name} 系列课程\n"
		case str() as s:
			extra_prefix = f"{s} 系列课程\n"

	if schedules:
		earliest_schedule = schedules[0]
		link_schedule = sorted(schedules, key = lambda s: prior.index(s.flag))[0]
		timing = "{START} – {END} {TZTEXT}".format(
			START = earliest_schedule.datetimeStart(form = "%-m 月 %-d 日 %-H:%M"),
			END = earliest_schedule.datetimeEnd(form = "%-H:%M"),
			TZTEXT = tz_text(earliest_schedule.timeStart))
		keyboard = [[["预约课程", link_schedule.url]]]
	else:
		from re import findall
		try:
			date = findall(VALIDDATES, course.slug)[0][1]
			vals = ValidDates(date, datetime.now())
			timing = f" 或 ".join(i.strftime("%Y 年 %-m 月 %-d 日") for i in vals)
		except IndexError:
			timing = "尚无可确定的课程时间"
		keyboard = [[["了解课程", course.url]]]
	keyboard[0].append(["下载图片", course.images["landscape"]])

	body = [disMarkdown(t) for t in ("#TodayatApple 新课程", f"{extra_prefix}*{course.name}*",
		f"🗺️ {stores_text}\n🕘 {timing}", f"*课程简介*\n{course.description["long"]}")]
	image = course.images["landscape"] + "?output-format=jpg&output-quality=80&resize=1280:*"
	return "\n\n".join(body), image, keyboard

async def post(text: str, image: str, keyboard: list[list[list[str]]]) -> None:
	from bot import async_post, chat_ids
	push = {"mode": "photo-text", "text": text, "image": image,
		"parse": "MARK", "chat_id": chat_ids[0], "keyboard": keyboard}
	await async_post(push)

async def entry(saved: dict[str, Any], mode: str,
	flags: list[str], session: SessionType) -> Optional[dict[str, Any]]:
	append = False
	courses: dict[Course, set[Schedule]] = {}
	results: list[Collection | Course | Schedule] = []

	match mode:
		case "today":
			stores = Peers(storeReturn(flags, opening = True), fast = True)
			tasks = [Store(store = store).getSchedules(ensure = False, session = session) for store in stores]
		case "sitemap":
			tasks = [Sitemap(flag = flag).getObjects(extend_schedule = True, session = session) for flag in flags]
		case _:
			return
	gathered = await AsyncGather(tasks, return_exceptions = True)
	runners, exp = [[i for i in gathered if b ^ isinstance(i, Exception)] for b in (True, False)]
	for e in exp:
		assert isinstance(e, Exception)
		logging.error(repr(e))
	r = {i for j in runners if isinstance(j, list) for i in j}
	course_collection, schedule = [[i for i in r if b ^ isinstance(i, Schedule)] for b in (True, False)]
	results = sorted(course_collection, key = lambda v: flags.index(v.flag)) + sorted(schedule)

	for j in results:
		match j:
			case Schedule(course = c):
				courses.setdefault(c, set()).add(j)
			case Course() as c:
				courses.setdefault(c, set())

	for course in courses:
		do_send = False
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
				text, image, keyboard = generate_collection(collection = collection)
				await post(text, image, keyboard)

		match conditions:
			case True, True, _:
				if course.flag not in saved["today"][course.courseId]["names"]:
					append = True
					saved["today"][course.courseId]["names"][course.flag] = course.name
			case True, False, _:
				append = do_send = True
				saved["today"][course.courseId] = {"slug": course.slug, "names": {course.flag: course.name}}
			case False, False, False:
				append = True
				if course.courseId not in saved["sitemap"]:
					do_send = True
					saved["sitemap"][course.courseId] = {"slug": course.slug, "names": {}}
				saved["sitemap"][course.courseId]["names"][course.flag] = course.name
		if conditions[0] and course.courseId in saved["sitemap"]:
			append = do_send = True
			del saved["sitemap"][course.courseId]

		if do_send:
			logging.info(str(course))
			all_schedules = [s for c, schedules in courses.items()
				if c.courseId == course.courseId for s in schedules]
			text, image, keyboard = generate_course(course = course, schedules = all_schedules, prior = flags)
			await post(text, image, keyboard)

	if append:
		saved["update"] = f"{datetime.now():%F %T}"
		return saved

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	fp = Path("Retail/savedEvent.json")
	logging.info("程序启动")
	saved = json.loads(fp.read_text())
	mode = "sitemap" if args.sitemap else "today"
	results = await entry(saved, mode, args.flags, session)
	if results:
		logging.info(f"正在更新 {fp} 文件")
		fp.write_text(json.dumps(sortOD(saved, reverse = [True, False]), ensure_ascii = False, indent = 2))
	logging.info("程序结束")

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("flags", metavar = "FLAG", type = str, nargs = "*",
		help = "指定国家或地区旗帜", default = DEFAULT_FLAGS)
	parser.add_argument("-d", "--debug", action = "store_true", help = "打印调试信息")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	parser.add_argument("-s", "--sitemap", action = "store_true", help = "网站地图模式")
	args = parser.parse_args()
	setLogger(logging.INFO, __file__, base_name = True, force_print = args.debug)
	asyncio.run(main(args))