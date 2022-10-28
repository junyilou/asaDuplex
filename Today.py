import os
import re
import json
import asyncio
import logging
from datetime import datetime, timezone
from sys import argv
from collections import OrderedDict

from storeInfo import *
from modules.today import Store, Sitemap, Collection, teleinfo, clean
from modules.util import setLogger, sync
from bot import chat_ids
from sdk_aliyun import async_post as raw_post

def sortOD(od, reverse = True):
	res = OrderedDict()
	for k, v in sorted(od.items(), reverse = reverse):
		if isinstance(v, dict):
			res[k] = sortOD(v, False)
		else:
			res[k] = v
	return res

def rec(lst, rst):
	for i in lst:
		match i:
			case list():
				rec(i, rst)
			case Exception():
				logging.error(str(i.args) if i.args else str(i))
			case _:
				if i not in rst:
					rst.append(i)
	return rst

async def async_post(text, image, keyboard):
	push = {
		"mode": "photo-text",
		"text": text,
		"image": image,
		"parse": "MARK",
		"chat_id": chat_ids[0],
		"keyboard": keyboard
	}
	await raw_post(push)

async def main(mode):
	global append
	match mode:
		case "today":
			stores = storeReturn(args["today"], needSplit = True, remove_closed = True, remove_future = True)
			tasks = [Store(sid = sid).getSchedules() for sid, sn in stores]
		case "sitemap":
			tasks = [Sitemap(rootPath = i).getObjects() for i in args["sitemap"]]
		case _:
			return
	
	courses = {}
	results = await asyncio.gather(*tasks, return_exceptions = True)
	results = rec(results, [])

	for j in results:
		if hasattr(j, "scheduleId"):
			courses[j.course] = courses.get(j.course, [])
			if j not in courses[j.course]:
				courses[j.course].append(j)
		else:
			courses[j] = courses.get(j, [])

	for course in courses:
		doSend = False
		toSave = {"slug": course.slug, "names": {course.flag: course.name}}
		conditions = [len(courses[course]) > 0] + [course.courseId in saved[s] for s in ["today", "sitemap"]]

		if isinstance((collection := course.collection), Collection):
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
			text, image, keyboard = teleinfo(course = course, schedules = sorted(schedules))
			await async_post(text, image, keyboard)

if __name__ == "__main__":
	args = {
		"today": "🇨🇳,🇭🇰,🇲🇴,🇹🇼,🇯🇵,🇰🇷,🇸🇬,🇹🇭",
		"sitemap": ".cn /hk /mo /tw /jp /kr /sg /th".split(" ")
	}

	append = False
	savedID = {}

	with open("Retail/savedEvent.json") as m: 
		saved = json.loads(m.read())
		for m in saved:
			savedID[m] = [i for i in saved[m]]

	if len(argv) == 1:
		argv = ["", "today"]

	setLogger(logging.INFO, os.path.basename(__file__))
	logging.info("程序启动")
	loop = sync(None)
	asyncio.set_event_loop(loop)
	loop.run_until_complete(main(argv[1]))
	clean(loop)

	if append:
		logging.info("正在更新 savedEvent 文件")
		saved["update"] = datetime.now(timezone.utc).strftime("%F %T GMT")
		with open("Retail/savedEvent.json", "w") as w:
			w.write(json.dumps(sortOD(saved), ensure_ascii = False, indent = 2))

	logging.info("程序结束")