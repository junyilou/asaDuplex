import os
import re
import json
import asyncio
import logging
from datetime import datetime
from sys import argv

from storeInfo import *
from modules.today import Store, Sitemap, teleinfo, __clean
from modules.constants import setLogger, sync
from bot import chat_ids
from sdk_aliyun import async_post

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
	collections = []
	times = 0
	for i in results:
		if isinstance(i, Exception):
			logging.error(str(i.args) if i.args else str(i))
			continue
		for j in i:
			if isinstance(j, Exception):
				logging.error(str(j.args) if j.args else str(j))
				continue

			c = j.course if hasattr(j, "scheduleId") else j
			if hasattr(c.collection, "slug"):
				if c.collection.slug not in saved["collection"]:
					collections.append(c.collection)
					append = {c.collection.slug: c.collection.name}
					saved["collection"] = {**saved["collection"], **append}
					logging.info(str(c.collection))
			if c.courseId not in savedID["today"]:
				if (mode == "today") or ((mode == "sitemap") 
				and (c.courseId not in savedID["sitemap"])):
					if c not in courses:
						courses[c] = []
						logging.info(str(c))
					if hasattr(j, "scheduleId"):
						if j not in courses[c]:
							courses[c].append(j)
							times += 1
							logging.info(str(j))
	logging.info(f"找到 {len(courses)} 个新课程共 {times} 次排课")

	for collection in collections:

		text, image, keyboard = teleinfo(collection = collection)

		push = {
			"mode": "photo-text",
			"text": text,
			"image": image,
			"parse": "MARK",
			"chat_id": chat_ids[0],
			"keyboard": keyboard
		}
		await async_post(push)

	for course in courses:
		schedules = sorted(courses[course])
		append = {course.courseId: course.name}
		if mode == "today":
			saved[mode] = {**saved[mode], **append}
			if course.courseId in saved["sitemap"]:
				del saved["sitemap"][course.courseId]
		elif mode == "sitemap":
			if schedules != []:
				saved["today"] = {**saved["today"], **append}
			else:
				saved[mode] = {**saved[mode], **append}

		text, image, keyboard = teleinfo(course = course, schedules = schedules)

		push = {
			"mode": "photo-text",
			"text": text,
			"image": image,
			"parse": "MARK",
			"chat_id": chat_ids[0],
			"keyboard": keyboard
		}
		await async_post(push)

if __name__ == "__main__":
	args = {
		"today": "🇨🇳，🇭🇰，🇲🇴，TW",
		"sitemap": ".cn /hk /mo /tw".split(" ")
	}

	append = {}
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
	__clean(loop)

	if append != {}:
		logging.info("正在更新 savedEvent 文件")

		with open("Retail/savedEvent.json", "w") as w:
			w.write(json.dumps(saved, ensure_ascii = False, indent = 2))

	logging.info("程序结束")