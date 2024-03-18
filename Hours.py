import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.constants import DIFFHTML
from modules.special import compare, special
from modules.util import SemaphoreType, SessionType, session_func, setLogger, sortOD
from storeInfo import Store, getStore, nameReplace, storeReturn

INCLUDE = "🇨🇳, 🇯🇵"
EXCLUDE = ""
USERLANG = "ZH"

WORKFILE = "Retail/storeHours.json"
RULEFILE = "Retail/storeHoursRules.json"

RUNTIME = datetime.now()
LOGSTRING = {
	"ZH": {
		"START": "程序启动",
		"END": "程序结束",
		"NEW": f"{'':8}{{DATE}} 新增: {{HOURS}}",
		"CHANGE": f"{'':8}{{DATE}} 变更: 由 {{HOURS1}} 改为 {{HOURS2}}",
		"CANCEL": f"{'':8}{{DATE}} 取消: {{HOURS}}",
		"COMMENT": f"{'':8}{{DATE}} 有新的评论:\n{'':12}{{COMMENT}}",
		"PREPS": "{LEN} 个零售店有特别营业时间变更",
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
		"PREPS": "{LEN} stores have special hours updates",
		"WRITE": "New storeHours.json generated",
		"NODIFF": "No updates found",
		"DIFFGEN": "DIFF storeHours.html generated",
		"DIFFCONTENT": "Apple Store Special Hours\nGenerated {RUNTIME}\n\nChanges:\n{DIFF}\n\nCalendar:\n{CALENDAR}\n\nRaw JSON:\n{JSON}"}}
LANG = LOGSTRING[USERLANG]

async def entry(store: Store, saved: dict[str, dict[str, str]], rules: dict[str, str],
	session: SessionType, semaphore: SemaphoreType) -> tuple[dict[str, dict[str, str]], list[str]]:
	async with semaphore:
		ans = await special(store, threshold = RUNTIME, userLang = USERLANG == "ZH", rules = rules, session = session)
	if ans is None:
		return saved, []

	diff: list[str] = []
	specials = saved | ans
	for date, opcode, *param in compare(saved, ans, threshold = f"{RUNTIME:%F}"):
		match opcode, param:
			case "new", [spe]:
				diff.append(LANG["NEW"].format(DATE = date, HOURS = spe))
			case "change", [svd, spe]:
				diff.append(LANG["CHANGE"].format(DATE = date, HOURS1 = svd, HOURS2 = spe))
			case "comment", [cmt]:
				diff.append(LANG["COMMENT"].format(DATE = date, COMMENT = cmt))
			case "cancel", [org]:
				specials.pop(date)
				diff.append(LANG["CANCEL"].format(DATE = date, HOURS = org))
			case "outdated", _:
				specials.pop(date)
				diff.append("")
				continue
		logging.info(f"[{store}] {date=} {opcode=} {param=}")
	return specials, diff

async def report(targets: list[Store]) -> None:
	from bot import chat_ids
	from botpost import async_post
	replaced = nameReplace(targets, number = False, final = str)
	text = f"{"、".join(replaced[:10])} 等 {len(targets)} 家零售店" if len(replaced) > 10 else "、".join(replaced)
	push = {"image": targets[0].dieter.split("?")[0],
		"mode": "photo-text", "chat_id": chat_ids[0], "parse": "MARK",
		"text": f'*来自 Hours 的通知*\n{text} 有特别营业时间更新 [↗](http://aliy.un/html/storeHours.html)'}
	await async_post(push)

@session_func
async def main(session: SessionType) -> None:
	file, rule = Path(WORKFILE), Path(RULEFILE)
	includes, excludes = [storeReturn(s, opening = True, split = True, allow_empty = False) for s in (INCLUDE, EXCLUDE)]
	stores = (i for i in includes if i not in excludes)

	if file.is_file():
		saved = json.loads(file.read_text())
		saved.pop("update", None)
		for v in saved.values():
			v.pop("storename", None)
	else:
		saved = {}
		file.write_text("{}")
	rules = json.loads(rule.read_text()) if rule.is_file() else {}

	semaphore = asyncio.Semaphore(20)
	async with asyncio.TaskGroup() as tg:
		tasks = {store: tg.create_task(entry(store,
			saved = saved.get(store.sid, {}),
			rules = rules.get(store.sid, {}),
			session = session, semaphore = semaphore)) for store in stores}

	diffs: dict[Store, list[str]] = {}
	targets: list[Store] = []
	calendar: dict[str, dict[Store, str]] = {}
	results: dict[Store, dict[str, dict[str, str]]] = {}
	for k, v in saved.items():
		if not k.isdigit():
			continue
		if (s := getStore(k)):
			results[s] = v

	for store, item in tasks.items():
		specials, diff = item.result()
		results[store] = specials
		if diff:
			diffs[store] = diff
		for date in specials:
			calendar.setdefault(date, {})[store] = specials[date]["special"]

	out: dict[str, Any] = {"update": f"{RUNTIME:%F %T}"}
	for k, v in sortOD(results).items():
		if not v:
			continue
		n = {a: b for a, b in v.items() if a >= f"{RUNTIME:%F}"}
		out.update({k.sid: n | {"storename": k.name}})
	cal: dict[str, dict[str, str]] = {dt: {k.name: v for k, v in dct.items()} for dt, dct in calendar.items()}
	file.rename(file.with_stem(f"{file.stem}-{RUNTIME:%y%m%d%H%M}"))
	file_text = json.dumps(out, ensure_ascii = False, indent = 2)
	file.write_text(file_text)
	logging.info(LANG["WRITE"])

	diff_str = []
	for store, diff in diffs.items():
		if not any(diff):
			continue
		diff_str.append(f"{'':4}{store}\n{"\n".join(diff)}")
		targets.append(store)
	if not diff_str:
		return logging.info(LANG["NODIFF"])
	logging.info(LANG["PREPS"].format(LEN = len(targets)))
	content = LANG["DIFFCONTENT"].format(
		RUNTIME = f"{RUNTIME:%F %T}", DIFF = "\n".join(diff_str), JSON = file_text,
		CALENDAR = json.dumps(cal, ensure_ascii = False, indent = 2, sort_keys = True))
	with open("html/storeHours.html", "w") as w:
		w.write(DIFFHTML.format(DIFFTITLE = "Special Hours", DIFFCONTENT = content))
	logging.info(LANG["DIFFGEN"])
	await report(targets)

setLogger(logging.INFO, __file__, base_name = True)
logging.info(LANG["START"])
asyncio.run(main())
logging.info(LANG["END"])