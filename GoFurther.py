import asyncio
import json
import logging
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import Any, Literal, Optional, TypedDict, TypeGuard

from modules.miniprogram import Mini, MiniProgram
from modules.regions import Region, RegionList, Regions
from modules.util import (AsyncGather, SessionType, disMarkdown, session_func,
                          setLogger)
from storeInfo import Store, storeReturn

type MasterType = MutableMapping[str, MutableMapping[str, Asset]]

class ContentMeta(TypedDict):
	poster: list[dict[str, str]]
	transcript: list[dict[str, str]]
	type: Literal["trailer"]

class ContentDict(TypedDict):
	id: str
	locale: str
	metadata: ContentMeta
	name: str
	sortOrder: int
	sources: list[str]
	title: str

class AmbientMeta(TypedDict):
	poster: list[dict[str, str]]
	type: Literal["ambient"]

class AmbientDict(TypedDict):
	id: str
	locale: str
	metadata: AmbientMeta
	name: str
	sortOrder: int
	sources: list[str]

class ExtraDict(TypedDict, total = False):
	ambient: str
	poster: str
	share: str
	transcript: str

def guard[T](dct: Mapping[str, Any], key: str, _: type[T]) -> TypeGuard[T]:
	try:
		return dct["metadata"]["type"] == key
	except KeyError:
		return False

@dataclass(order = True)
class Asset:
	collId: str
	title: str = ""
	source: str = field(default = "", repr = False)
	extra: ExtraDict = field(init = False, repr = False)
	region: Region = field(init = False)

	def __post_init__(self) -> None:
		self.extra = {}

	@property
	def index(self) -> tuple[str, str]:
		a, b = self.collId.rsplit("-", 1)
		return a, b

	@property
	def teleinfo(self) -> str:
		body = [f"{self.region.flag} *{self.region.name}*"]
		items: list[tuple[str, Optional[str]]] = [("播放", self.source),
			("封面", self.extra.get("poster")), ("封面视频", self.extra.get("ambient"))]
		for k, v in items:
			if v:
				body.append(f"{k} [↗]({v})")
		return " ".join(body)

async def entry(store: Store, mini: MiniProgram, session: SessionType) -> list[Asset]:
	try:
		logging.info(f"正请求 {store.region}")
		r = await mini.request("miniprogram/todayatapple/p/wechat/featured", session,
			assert_keyword = "featuredSessionResponse", params = {"store": store.rid})
	except AssertionError:
		logging.debug(f"请求 {store.region} 不成功")
		return []
	results: list[Asset] = []
	j = r["featuredSessionResponse"]["featured"]
	for item in j:
		if item.get("entityType") != "FEATURED_VIDEO":
			continue
		data = item["assets"][0]
		inst = Asset(collId = data["collateralId"])
		inst.region = store.region
		assets: list[ContentDict | AmbientDict] = data["assets"]
		for asset in assets:
			if guard(asset, "trailer", ContentDict):
				inst.title = asset.get("title", inst.collId).translate({0xa0: " "})
				inst.source = asset["sources"][0]
				for key in ("poster", "transcript"):
					if key in asset["metadata"]:
						inst.extra[key] = asset["metadata"][key][0]["source"]
			if guard(asset, "ambient", AmbientDict):
				inst.extra["ambient"] = asset["sources"][0]
		try:
			inst.extra["share"] = data["shareUrls"]["asa"]
		except KeyError:
			pass
		try:
			assert inst.title, "标题为空"
			assert inst.source, "资源链接为空"
		except AssertionError as e:
			logging.error(f"资源信息不完整 {inst.collId} @ {store.region}: {e}")
		else:
			results.append(inst)
	return results

async def report(arrivals: list[Asset]) -> None:
	from bot import async_post, chat_ids

	preferred_regions = [Regions["🇨🇳"], Regions["🇺🇸"], *RegionList]
	for _, combined in groupby(arrivals, key = lambda k: k.index[0]):
		sorted_assets = sorted(combined, key = lambda k: preferred_regions.index(k.region))
		title = sorted_assets[0].title
		lines = "\n".join(a.teleinfo for a in sorted_assets)
		text = f"*Apple Store \\#深入探索*\n\n{disMarkdown(title, extra = "*", wrap = "*")}\n{lines}"
		poster = next((i for i in (a.extra.get("poster") for a in sorted_assets) if i), None)
		push = {"mode": "text", "text": text, "chat_id": chat_ids[0], "parse": "MARK"}
		if poster:
			push["mode"], push["image"] = "photo", poster
		await async_post(push)

@session_func
async def main(session: SessionType) -> None:
	with open("Retail/gofurther.json") as r:
		db: dict[str, dict[str, str]] = json.load(r)
	mini = await Mini()
	lst = [next(r) for _, r in groupby(storeReturn(opening = 1), key = lambda k: k.flag)]
	results = await AsyncGather((entry(store, mini, session) for store in lst),
		limit = 3, return_exceptions = False)
	assets = sorted((i for j in results for i in j), key = lambda x: x.index)

	arrivals: list[Asset] = []
	for asset in assets:
		local = None
		slug, _ = asset.index
		rp = asset.region.abbr.lower()
		try:
			local = db[slug][rp]
			assert local == asset.source
			continue
		except AssertionError:
			exists = True
		except KeyError:
			exists = False
		if exists:
			logging.info(f"变更资源 {slug},{rp} {local} -> {asset.source}")
		else:
			logging.info(f"新资源 {asset!r}")
		arrivals.append(asset)
		db.setdefault(slug, {})[rp] = asset.source

	if arrivals:
		await report(arrivals)

	with open("Retail/gofurther.json", "w") as w:
		json.dump(db, w, indent = 2, ensure_ascii = False, sort_keys = True)

if __name__ == "__main__":
	setLogger(logging.INFO, __file__, base_name = True)
	logging.info("程序启动")
	asyncio.run(main())
	logging.info("程序结束")