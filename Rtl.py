import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Optional

import aiohttp

from modules.util import (SemaphoreType, SessionType, disMarkdown, get_session,
                          session_func, setLogger, with_semaphore)
from storeInfo import DEFAULTFILE, STORES, Store, sidify


async def post(store: Store, dt: datetime, raw: bytes) -> None:
	from bot import async_post, chat_ids, photo_encode
	texts = ["*零售店图片更新通知*", "", f"{store:telegram}", f"*远程标签* {dt:%F %T}"]
	buttons = [[["启动消息推送向导", f"RTLPOST {store.sid} NEW"]]]
	assert await async_post({"mode": "photo-text", "image": photo_encode(raw),
		"text": disMarkdown("\n".join(texts)), "chat_id": chat_ids[0],
		"keyboard": buttons, "parse": "MARK"})

async def task(store: Store,
	special_list: list[str],
	local_mode: bool,
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
	store.modify = dt.strftime("%F %T")
	if digest == getattr(store, "md5", None):
		logging.info(f"[{store.rid}] 图片实际上没有更新")
		return store
	if special:
		special_list.remove(store.sid)
	store.md5 = digest
	with open(f"Retail/{store.rid}-{dt:%F-%H%M%S}.png", "wb") as w:
		w.write(raw)
	if not local_mode:
		try:
			logging.info(f"[{store.rid}] 准备发送消息")
			await post(store, dt, raw)
		except Exception as exp:
			logging.warning(f"[{store.rid}] 发送消息失败: {exp!r}")
	return store

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	semaphore = asyncio.Semaphore(20)
	special_file = Path("specialists.json")
	special_list: list[str] = json.loads(special_file.read_text())
	sids = {sidify(s) for s in args.sids}
	if args.special:
		sids.update(special_list)
	elif not sids:
		sids.update(STORES)
	stores = [store for sid, store in STORES.items() if sid in sids]
	if not stores:
		return

	setLogger(logging.INFO, __file__, base_name = True)
	logging.info(f"准备查询 {len(stores)} 家零售店")
	tasks = [task(store, special_list, args.local, session, semaphore) for store in sorted(stores)]
	if args.debug:
		from tqdm.asyncio import tqdm_asyncio
		results = await tqdm_asyncio.gather(*tasks)
	else:
		results = await asyncio.gather(*tasks)
	if not any(results):
		return logging.info("没有找到更新")

	remote = STORES | {r.sid: r for r in results if isinstance(r, Store)}
	updated = {"_": datetime.now().strftime("%F %T"), "stores": {v.rid: v.dumps() for k, v in remote.items()}}
	if args.special:
		logging.info(f"更新特别观察列表: {special_list}")
		special_file.write_text(json.dumps(special_list))
	logging.info(f"更新门店数据文件: {updated["_"]}")
	Path(DEFAULTFILE).write_text(json.dumps(updated, ensure_ascii = False, indent = 2, sort_keys = True))
	logging.info("程序结束")

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("sids", metavar = "SID", type = str, nargs = "*", help = "手动给出店号")
	parser.add_argument("-d", "--debug", action = "store_false", help = "不打印调试信息")
	parser.add_argument("-l", "--local", action = "store_true", help = "仅限本地运行")
	parser.add_argument("-s", "--special", action = "store_true", help = "从特别列表读取店号")
	args = parser.parse_args()
	asyncio.run(main(args))