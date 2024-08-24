import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime
from functools import partial
from itertools import chain
from pathlib import Path
from random import choice, shuffle
from typing import Any

from modules.special import compare, special
from modules.util import AsyncGather, SessionType, session_func, setLogger
from storeInfo import Store, getStore, nameReplace, storeReturn

RUNTIME = datetime.now()
LANG = {
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
	"DIFFCONTENT": "Apple Store 特别营业时间\n生成于 {RUNTIME}\n\n"
		"变化:\n{DIFF}\n\n日历:\n{CALENDAR}\n\n原始 JSON:\n{JSON}"}
DIFFHTML = '<!DOCTYPE html><head><meta charset="utf-8">\
<meta name="viewport" content="width=device-width, initial-scale=1.0">\
<title>{DIFFTITLE}</title></head><body><pre><code>{DIFFCONTENT}</code></pre></body></html>'

async def entry(store: Store, saved: dict[str, dict[str, str]], rules: dict[str, str],
	session: SessionType) -> tuple[dict[str, dict[str, str]], list[str]]:
	ans = await special(store, threshold = RUNTIME, rules = rules, session = session)
	if ans is None:
		return saved, []

	diff: list[str] = []
	specials = {i: saved.get(i, {}) | ans.get(i, {}) for i in chain(saved, ans)}
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
	push = {"image": choice(targets).dieter.split("?")[0],
		"mode": "photo-text", "chat_id": chat_ids[0], "parse": "MARK",
		"text": f'*来自 Hours 的通知*\n{text} 有特别营业时间更新 [↗](http://aliy.un/hours)'}
	await async_post(push)

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	store_return = partial(storeReturn, opening = True, allow_empty = False)
	includes, excludes = [store_return(s) for s in (args.include, args.exclude)]
	stores = [i for i in includes if i not in excludes]
	shuffle(stores)

	file, rule = args.file, args.rule
	saved = json.loads(file.read_text())["stores"] if file.is_file() else {}
	rules = json.loads(rule.read_text()) if rule.is_file() else {}

	remote = await AsyncGather((entry(store,
		saved = saved.get(store.rid, {}).get("dates", {}),
		rules = rules.get(store.rid, {}),
		session = session) for store in stores), limit = 20)

	diffs: dict[Store, list[str]] = {}
	targets: list[Store] = []
	calendar: dict[str, dict[Store, str]] = {}
	results: dict[Store, dict[str, dict[str, str]]] = {}
	for k, v in saved.items():
		if s := getStore(k):
			results[s] = v.get("dates", {})

	for store, (specials, diff) in zip(stores, remote):
		results[store] = specials
		if diff:
			diffs[store] = diff
		for date in specials:
			calendar.setdefault(date, {})[store] = specials[date]["special"]

	diff_str = []
	for store, diff in sorted(diffs.items()):
		if not any(diff):
			continue
		diff_str.append(f"{'':4}{store}\n{"\n".join(diff)}")
		targets.append(store)
	if not diff_str:
		return logging.info(LANG["NODIFF"])

	out: dict[str, Any] = {"_": f"{RUNTIME:%F %T}"}
	out["stores"] = {i: j for i, j in {k.rid: {"name": k.name,
		"dates": {d: t for d, t in v.items() if d >= f"{RUNTIME:%F}"}}
		for k, v in results.items()}.items() if j.get("dates")}
	file.rename(file.with_stem(f"{file.stem}-{RUNTIME:%y%m%d%H%M}"))
	file_text = json.dumps(out, ensure_ascii = False, indent = 2)
	file.write_text(file_text)
	logging.info(LANG["WRITE"])

	logging.info(LANG["PREPS"].format(LEN = len(targets)))
	hfile = Path("ecs/hours/index.html")
	if hfile.exists():
		hfile.rename(hfile.with_stem(f"history-{datetime.fromtimestamp(hfile.stat().st_ctime):%Y%m%d-%H%M%S}"))
	cal: dict[str, dict[str, str]] = {dt: {k.name: v for k, v in sorted(dct.items())} for dt, dct in calendar.items()}
	content = LANG["DIFFCONTENT"].format(
		RUNTIME = f"{RUNTIME:%F %T}", DIFF = "\n".join(diff_str), JSON = file_text,
		CALENDAR = json.dumps(cal, ensure_ascii = False, indent = 2, sort_keys = True))
	hfile.write_text(DIFFHTML.format(DIFFTITLE = "Special Hours", DIFFCONTENT = content))
	logging.info(LANG["DIFFGEN"])

	if args.local:
		return
	await report(targets)

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("include", metavar = "INCLUDE", type = str, nargs = "*", help = "包含的零售店列表")
	parser.add_argument("--exclude", action = "append", default = [], help = "不包含的零售店列表")
	parser.add_argument("--file", default = "Retail/storeHours.json", type = Path, help = "工作文件目录")
	parser.add_argument("--rule", default = "Retail/storeHoursRules.json", type = Path, help = "规则文件目录")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	args = parser.parse_args()
	setLogger(logging.INFO, __file__, base_name = True)
	logging.info(LANG["START"])
	asyncio.run(main(args))
	logging.info(LANG["END"])