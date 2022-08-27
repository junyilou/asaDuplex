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

def sortOD(od, topLevel = True):
    res = OrderedDict()
    for k, v in sorted(od.items(), reverse = topLevel):
        if isinstance(v, dict):
            res[k] = sortOD(v, False)
        else:
            res[k] = v
    return res

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
	if mode == "today":
		stores = storeReturn(args["today"], needSplit = True, remove_closed = True, remove_future = True)
		tasks = [Store(sid = sid).getSchedules() for sid, sn in stores]
	elif mode == "sitemap":
		tasks = [Sitemap(rootPath = i) for i in args["sitemap"]]
	else:
		return
	results = await asyncio.gather(*tasks, return_exceptions = True)

	courses = {}
	for i in results:
		if isinstance(i, Exception):
			logging.error(str(i.args) if i.args else str(i))
			continue
		
		for j in i:
			if isinstance(j, Exception):
				logging.error(str(j.args) if j.args else str(j))
				continue

			if hasattr(j, "scheduleId"):
				courses[j.course] = courses.get(j.course, [])
				if j not in courses[j.course]:
					courses[j.course].append(j)

	for course in courses:
		collection = course.collection
		cond1, cond2 = [course.courseId in saved[cond] for cond in ["today", "sitemap"]]
		cond3 = isinstance(collection, Collection)
		cond4 = cond3 and collection.slug in saved["collection"]
		
		if cond1 and cond2:
			tempo = None
		elif cond1 and not cond2:
			tempo = "today"
		elif not cond1:
			append = True
			tempo = "sitemap"
			if courses[course] != []:
				saved["today"][course.courseId] = {
					"slug": course.slug,
					course.flag: course.name
				}
				if cond2:
					del saved["sitemap"][course.courseId][course.flag]
					if len(saved["sitemap"][course.courseId].keys()) == 1:
						del saved["sitemap"][course.courseId]
					tempo = None

			logging.info(str(course))
			schedules = [j for i in (courses[c] for c in courses if c.courseId == course.courseId) for j in i]
			text, image, keyboard = teleinfo(course = course, schedules = sorted(schedules))
			await async_post(text, image, keyboard)

		if tempo != None:
			if course.courseId in saved[tempo]:
				if course.flag not in saved[tempo][course.courseId]:
					append = True
					saved[tempo][course.courseId][course.flag] = course.name

		if cond3 and not cond4:
			append = True
			saved["collection"][collection.slug] = {course.flag: collection.name}
			logging.info(str(collection))
			text, image, keyboard = teleinfo(collection = collection)
			await async_post(text, image, keyboard)

		elif cond3 and cond4:
			if course.flag not in saved["collection"][collection.slug]:
				append = True
				saved["collection"][collection.slug][course.flag] = collection.name


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