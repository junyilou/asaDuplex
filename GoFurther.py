import asyncio
import json
import logging
from dataclasses import dataclass
from itertools import groupby

from modules.miniprogram import Mini, MiniProgram
from modules.regions import Region
from modules.util import (AsyncGather, SessionType, disMarkdown, session_func,
                          setLogger)
from storeInfo import Store, storeReturn


@dataclass(order = True)
class Asset:
	region: Region
	id: str
	locale: str
	title: str
	url: str
	poster: str

	def teleinfo(self) -> str:
		title = disMarkdown(self.title, wrap = "*", extra = "*")
		items = [("视频文件", self.url), ("封面图片", self.poster)]
		links = " ".join(f"{k} [↗]({v})" for k, v in items if v)
		body = f"{self.region.flag} *{self.region.name}* {links}"
		return "\n".join((title, body))

async def entry(mini: MiniProgram, store: Store, session: SessionType) -> list[Asset]:
	logging.info(f"正请求 {store.region} ({store.rid})")
	r = await mini.request("miniprogram/todayatapple/p/wechat/featured", session,
		assert_keyword = "featuredSessionResponse", params = {"store": store.rid})
	assets = [Asset(region = store.region, id = asset["id"], locale = asset["locale"],
		title = asset["title"], url = asset["sources"][0], poster = next(
		(s for p in asset["metadata"]["poster"] if (s := p.get("source"))), ""))
		for feature in r["featuredSessionResponse"]["featured"]
		if feature.get("entityType") == "FEATURED_VIDEO"
		for assets in feature["assets"] for asset in assets["assets"]
		if store.region.abbr in asset["locale"] and "title" in asset]
	return assets

async def report(arrivals: list[Asset], master: dict[str, dict[str, str]]) -> None:
	from bot import async_post, chat_ids

	body = [f"*Apple Store \\#深入探索*\n找到 {len(arrivals)} 个新资源"]
	for a in arrivals:
		master.setdefault(a.region.flag, {})[a.id] = a.url
		body.append(a.teleinfo())
	poster = next((a.poster for a in arrivals if a.poster), None)
	push = {"mode": "text", "text": "\n\n".join(body), "chat_id": chat_ids[0], "parse": "MARK"}
	if poster:
		push["mode"], push["image"] = "photo", poster
	await async_post(push)

@session_func
async def main(session: SessionType) -> None:
	with open("gofurther.json") as r:
		j: dict[str, dict[str, str]] = json.load(r)

	mini = await Mini(session)
	if not mini.prefix:
		logging.error("加载小程序前缀失败")
		return

	lst = [next(r) for _, r in groupby(storeReturn(opening = 1), key = lambda k: k.flag)]
	results = await AsyncGather((entry(mini, s, session) for s in lst),
		limit = 10, return_exceptions = True)

	arrivals: list[Asset] = []
	for s, r in zip(lst, results):
		region, result = s.region, [] if isinstance(r, Exception) else r
		arrivals.extend(r for r in result if r.id not in j.get(region.flag, {}))
	arrivals.sort()

	if not arrivals:
		logging.info("没有找到新资源")
		return
	logging.info(f"找到 {len(arrivals)} 个新资源")
	await report(arrivals, j)
	logging.info("写入文件")
	with open("gofurther.json", "w") as w:
		json.dump(j, w, indent = 2, ensure_ascii = False, sort_keys = True)

setLogger(logging.INFO, __file__, base_name = True)
logging.info("程序启动")
asyncio.run(main())
logging.info("程序结束")