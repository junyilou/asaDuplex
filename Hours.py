import asyncio
import json
import logging
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Optional

from modules.util import SemaphoreType, SessionType, session_func, setLogger, sortOD
from modules.special import special
from modules.constants import DIFFHTML
from storeInfo import Store, nameReplace, storeReturn

INCLUDE = "🇨🇳, 🇯🇵"
EXCLUDE = "609"
WORKFILE = "Retail/storeHours.json"
USERLANG = "ZH"

RUNTIME = datetime.now()
LOGSTRING = {
	"ZH": {
		"START": "程序启动",
		"END": "程序结束",
		"NEW": f"{'':8}{{DATE}} 新增: {{HOURS}}",
		"CHANGE": f"{'':8}{{DATE}} 变更: 由 {{HOURS1}} 改为 {{HOURS2}}",
		"CANCEL": f"{'':8}{{DATE}} 取消: {{HOURS}}",
		"COMMENT": f"{'':8}{{DATE}} 有新的评论:\n{'':12}{{COMMENT}}",
		"PREPS": "{STORE} 个零售店有 {DIFF} 条特别营业时间变更",
		"WRITE": "已写入新的 storeHours.json",
		"NODIFF": "没有发现 storeHours 文件更新",
		"DIFFGEN": "已生成对比文件 storeHours.html",
		"DIFFCONTENT": "Apple Store 特别营业时间\n生成于 {RUNTIME}\n\n变化:\n{DIFF}\n\n日历:\n{CALENDAR}\n\n原始 JSON:\n{JSON}"},
	"EN": {
		"START": "Program Started",
		"END": "Program Ended",
		"NEW": f"{'':8}{{DATE}} New: {{HOURS}}",
		"CHANGE": f"{'':8}{{DATE}} Changed: from {{HOURS1}} to {{HOURS2}}",
		"CANCEL": f"{'':8}{{DATE}} Canceled: {{HOURS}}",
		"COMMENT": f"{'':8}{{DATE}} New Comment:\n{'':12}{{COMMENT}}",
		"PREPS": "{STORE} stores have {DIFF} diff messages",
		"WRITE": "New storeHours.json generated",
		"NODIFF": "No updates found",
		"DIFFGEN": "DIFF storeHours.html generated",
		"DIFFCONTENT": "Apple Store Special Hours\nGenerated {RUNTIME}\n\nChanges:\n{DIFF}\n\nCalendar:\n{CALENDAR}\n\nRaw JSON:\n{JSON}"}}
LANG = LOGSTRING[USERLANG]

async def entry(store: Store, saved: Optional[dict[str, dict[str, str]]],
	session: SessionType, semaphore: SemaphoreType) -> tuple[dict[str, dict[str, str]], list[str]]:
	saved = saved or {}
	async with semaphore:
		ans = await special(store, threshold = RUNTIME, userLang = USERLANG == "ZH", session = session)
	if ans is None:
		return saved, []

	diff: list[str] = []
	specials = saved | ans

	for date, detail in ans.items():
		spe = detail["special"]
		if date not in saved:
			diff.append(LANG["NEW"].format(DATE = date, HOURS = spe))
		elif (svd := saved[date]["special"]) != spe:
			diff.append(LANG["CHANGE"].format(DATE = date, HOURS1 = svd, HOURS2 = spe))
		elif not saved[date].get("comment") and detail.get("comment"):
			diff.append(LANG["COMMENT"].format(DATE = date, COMMENT = detail["comment"]))

	for date, detail in saved.items():
		if date == "storename":
			continue
		if date < f"{RUNTIME:%F}":
			specials.pop(date)
			continue
		if date not in ans:
			specials.pop(date)
			diff.append(LANG["CANCEL"].format(DATE = date, HOURS = detail["special"]))

	if diff:
		logging.info(f"[{store.telename(sid = False)}] " + ", ".join(
			i.lstrip() for i in "\n".join(diff).split("\n")))

	return specials, diff

async def report(targets: list[Store]) -> None:
	from bot import chat_ids
	from botpost import async_post
	replaced = nameReplace(targets, number = False, final = lambda s: s.telename(sid = False))
	text = f"{"、".join(replaced[:10])} 等 {len(targets)} 家零售店" if len(replaced) > 10 else "、".join(replaced)
	push = {"image": targets[0].dieter.split("?")[0],
		"mode": "photo-text", "chat_id": chat_ids[0], "parse": "MARK",
		"text": f'*来自 Hours 的通知*\n{text} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)'}
	await async_post(push)

@session_func
async def main(session: SessionType) -> None:
	file = Path(WORKFILE)
	includes, excludes = map(partial(storeReturn, split = True, opening = True), (INCLUDE, EXCLUDE))
	stores = (i for i in includes if i not in excludes)

	if file.is_file():
		saved = json.loads(file.read_text())
		for v in saved.values():
			if isinstance(v, dict):
				v.pop("storename", None)
	else:
		saved = {}
		file.write_text("{}")

	semaphore = asyncio.Semaphore(20)
	async with asyncio.TaskGroup() as tg:
		tasks = {store: tg.create_task(entry(store, saved.get(store.sid), session, semaphore)) for store in stores}

	diffs: list[str] = []
	targets: list[Store] = []
	calendar: dict[str, dict[Store, str]] = {}
	results: dict[Store, dict[str, dict[str, str]]] = {}

	for store, item in tasks.items():
		specials, diff = item.result()
		if len(specials):
			results[store] = specials
		if diff:
			diffs.append(f"{'':4}{store.telename(sid = False)}")
			diffs.extend(diff)
			targets.append(store)
		for date in specials:
			calendar.setdefault(date, {})[store] = specials[date]["special"]
	if not diffs:
		return logging.info(LANG["NODIFF"])

	logging.info(LANG["PREPS"].format(STORE = len(targets), DIFF = len(diffs)))
	out: dict[str, Any] = {"update": f"{RUNTIME:%F %T}"}
	for k, v in sortOD(results).items():
		out.update({k.sid: v | {"storename": k.name}})
	cal: dict[str, dict[str, str]] = {dt: {k.name: v for k, v in dct.items()} for dt, dct in calendar.items()}
	file.rename(file.with_stem(f"{file.stem}-{RUNTIME:%y%m%d%H%M}"))
	file_text = json.dumps(out, ensure_ascii = False, indent = 2)
	file.write_text(file_text)
	logging.info(LANG["WRITE"])

	content = LANG["DIFFCONTENT"].format(
		RUNTIME = f"{RUNTIME:%F %T}", DIFF = "\n".join(diffs), JSON = file_text,
		CALENDAR = json.dumps(cal, ensure_ascii = False, indent = 2, sort_keys = True))
	with open("html/storeHours.html", "w") as w:
		w.write(DIFFHTML.format(DIFFTITLE = "Special Hours", DIFFCONTENT = content))
	logging.info(LANG["DIFFGEN"])

	await report(targets)

setLogger(logging.INFO, __file__, base_name = True)
logging.info(LANG["START"])
asyncio.run(main())
logging.info(LANG["END"])