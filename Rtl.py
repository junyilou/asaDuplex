import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime
from hashlib import md5
from sys import argv
from typing import Optional, cast

import aiohttp

from modules.util import (SemaphoreType, SessionType, disMarkdown, get_session,
                          session_func, setLogger, with_semaphore)
from storeInfo import Store, StoreDict, storeReturn


async def post(store: Store, dt: datetime, raw: bytes) -> None:
	from bot import chat_ids
	from botpost import async_post, photo_encode
	texts = ["*零售店图片更新通知*", "", f"{store:telegram}", f"*远程标签* {dt:%F %T}"]
	buttons = [[["启动消息推送向导", f"RTLPOST {store.sid} NEW"]]]
	assert await async_post({"mode": "photo-text", "image": photo_encode(raw),
		"text": disMarkdown("\n".join(texts)), "chat_id": chat_ids[0],
		"keyboard": buttons, "parse": "MARK"})

async def task(store: Store,
	special_list: list[str],
	session: Optional[SessionType] = None,
	semaphore: Optional[SemaphoreType] = None) -> Optional[Store]:
	special = store.sid in special_list

	def judge(head: Mapping[str, str]) -> Optional[datetime]:
		dt = datetime.strptime(head["Last-Modified"], "%a, %d %b %Y %H:%M:%S GMT")
		local = getattr(store, "modify", None)
		if local and local > dt.strftime("%F %T"):
			if special:
				logging.info(f"[{store.rid}] 记录到无效时间")
			return
		elif local == dt.strftime("%F %T"):
			if special:
				logging.info(f"[{store.rid}] 图片没有更新")
			return
		logging.info(f"[{store.rid}] 记录到新时间 {dt:%F %T}")
		return dt

	async with with_semaphore(semaphore):
		async with get_session(session) as ses:
			try:
				async with ses.get(store.dieter, ssl = False, raise_for_status = True) as request:
					head = request.headers
					if not (dt := judge(head)):
						return
					raw = await request.read()
					assert isinstance(raw, bytes) and raw
			except aiohttp.ClientResponseError as cre:
				if cre.status == 404:
					return
				logging.error(f"[{store.rid}] 网络请求失败: {cre!r}")
				return
			except Exception as exp:
				logging.error(f"[{store.rid}] 运行时异常: {exp!r}")
				return

	digest = md5(raw).hexdigest()
	store.raw["modify"] = dt.strftime("%F %T")
	if digest == getattr(store, "md5", None):
		logging.info(f"[{store.rid}] 图片实际上没有更新")
		return store
	if special:
		special_list.remove(store.sid)
	store.raw["md5"] = digest
	try:
		with open(f"Retail/{store.rid}-{dt:%F-%H%M%S}.png", "wb") as w:
			w.write(raw)
		logging.info(f"[{store.rid}] 准备发送消息")
		await post(store, dt, raw)
	except Exception as exp:
		logging.warning(f"[{store.rid}] 发送消息失败: {exp!r}")
	return store

@session_func
async def main(session: SessionType) -> None:
	semaphore = asyncio.Semaphore(20)
	with open("storeInfo.json") as r:
		j = json.load(r)
		j.pop("update")
		p = cast(dict[str, StoreDict], j)

	judge_remove = lambda k: not (k not in argv or (argv.remove(k) or False))
	print_progress = judge_remove("print")
	mode = argv[1:] or ["normal"]
	match mode:
		case ["normal" | "single" as mode, *ids]:
			sids, l = set(), []
			for i in ids:
				sids.update(j.sid for j in storeReturn(i, remove_internal = True))
			stores = [Store(s, d) for s, d in p.items() if mode == "normal" or s in sids]
		case ["special", *_]:
			with open("specialists.json") as r:
				l = cast(list[str], json.load(r))
			stores = [Store(s, d) for s, d in p.items() if s in l]
		case _:
			stores, l = [], []

	if not stores:
		return
	setLogger(logging.INFO, __file__, base_name = True)
	logging.info(f"准备查询 {len(stores)} 家零售店")
	tasks = [task(store, l, session, semaphore) for store in stores]
	if print_progress:
		from tqdm.asyncio import tqdm_asyncio
		results = await tqdm_asyncio.gather(*tasks)
	else:
		results = await asyncio.gather(*tasks)

	write = False
	for r in results:
		if not isinstance(r, Store):
			continue
		write = True
		j[r.sid] = r.raw
	if write:
		if mode[0] == "special":
			logging.info(f"更新特别观察列表: {l}")
			with open("specialists.json", "w") as w:
				json.dump(l, w)
		j["update"] = dt = f"{datetime.now():%F %T}"
		logging.info(f"更新门店数据文件: {dt}")
		with open("storeInfo.json", "w") as w:
			json.dump(j, w, ensure_ascii = False, indent = 2, sort_keys = True)
	logging.info("程序结束")

if __name__ == "__main__":
	asyncio.run(main())