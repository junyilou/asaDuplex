import asyncio
import json
import logging
from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from modules.regions import Regions
from modules.today import Collection, Course
from modules.util import SessionType, get_session, session_func, setLogger

FLAGS = [flag for flag, region in Regions.items() if region.url_taa is not None]

async def test(func: type[Course] | type[Collection],
	slug: str, flags: list[str] = FLAGS,
	session: Optional[SessionType] = None) -> bool:
	semaphore = asyncio.Semaphore(3)

	async def entry(rootPath: str, ses: SessionType) -> Optional[Collection | Course]:
		try:
			async with semaphore:
				logging.debug(f"[测试] {slug=} {rootPath=}")
				return await func.get(rootPath, slug, session = ses)
		except Exception:
			return

	logging.info(f"[开始] {slug=} {len(flags)=}")
	async with get_session(session) as ses:
		tasks = [asyncio.create_task(entry(Regions[flag].url_taa or "", ses)) for flag in flags]
	for task in asyncio.as_completed(tasks):
		if await task:
			try:
				for t in tasks:
					t.cancel()
			except:
				pass
			logging.info(f"[找到] {slug=}")
			return True
	logging.info(f"[未找到] {slug=}")
	return False

class File:
	def __init__(self, path: str) -> None:
		self.path = Path(path)
		logging.info(f"[读取文件] {self.path}")
		self.fp = json.loads(self.path.read_text())
		self.semaphore = asyncio.Semaphore(3)

	def pre_write(self) -> None:
		...

	async def run(self, session: Optional[SessionType] = None) -> list[str]:
		...

	async def main(self, session: Optional[SessionType] = None) -> None:
		if results := await self.run(session):
			results.sort(key = lambda x: x.split("-")[-1])
			logging.info(f"[删除] {len(results)=}")
			for result in results:
				logging.info(f"[删除] {result}")
			logging.info(f"[写入文件] {self.path}")
			self.pre_write()
			self.path.write_text(json.dumps(self.fp, indent = 2, ensure_ascii = False))
			return
		logging.info("[无删除]")

class AssuredFile(File):
	def __init__(self) -> None:
		return super().__init__("Retail/assured-events.json")

	async def entry(self, key: str, session: SessionType) -> Optional[str]:
		async with self.semaphore:
			if not await test(Course, self.fp[key], session = session):
				return self.fp.pop(key)

	async def run(self, session: Optional[SessionType] = None) -> list[str]:
		async with get_session(session) as ses:
			results = await asyncio.gather(*[self.entry(key, ses) for key in self.fp])
		return [i for i in results if i]

class SavedEventFile(File):
	def __init__(self) -> None:
		return super().__init__("Retail/savedEvent.json")

	def pre_write(self) -> None:
		self.fp["update"] = datetime.now().strftime("%F %T")

	async def entry(self, func: type[Course] | type[Collection],
		fp: dict, key: str, session: SessionType) -> Optional[str]:
		async with self.semaphore:
			if func is Course:
				slug, flags = fp[key]["slug"], list(fp[key]["names"])
			else:
				slug, flags = key,list(fp[key])
			if not await test(func, slug, flags, session):
				del fp[key]
				return slug

	async def run(self, session: Optional[SessionType] = None) -> list[str]:
		async with get_session(session) as ses:
			coros = []
			for k in ("today", "sitemap", "collection"):
				for key in (fp := self.fp.get(k, {})):
					func = Collection if k == "collection" else Course
					coros.append(self.entry(func, fp, key, ses))
			results = await asyncio.gather(*coros)
		return [i for i in results if i]

class FindASessionFile(File):
	def __init__(self) -> None:
		return super().__init__("Retail/findasession.json")

	def pre_write(self) -> None:
		self.fp["update"] = datetime.now(UTC).strftime("%F %T GMT")

	async def entry(self, func: type[Course] | type[Collection],
		key: str, session: SessionType) -> Optional[str]:
		async with self.semaphore:
			if func is Course:
				fp = self.fp["course"]
				slug = fp[key]["slug"]
			else:
				fp = self.fp["collection"]
				slug = key
			flags = fp[key]["flags"]
			if not await test(func, slug, flags, session):
				del fp[key]
				return slug

	async def run(self, session: Optional[SessionType] = None) -> list[str]:
		async with get_session(session) as ses:
			coros = [self.entry(Course, key, ses) for key in self.fp["course"]]
			coros.extend([self.entry(Collection, key, ses) for key in self.fp["collection"]])
			results = await asyncio.gather(*coros)
		return [i for i in results if i]

@session_func
async def main(session: SessionType, args: Namespace) -> None:
	if args.assured:
		file = AssuredFile()
	elif args.findasession:
		file = FindASessionFile()
	elif args.saved:
		file = SavedEventFile()
	else:
		return
	await file.main(session)

if __name__ == "__main__":
	parser = ArgumentParser()
	parser.add_argument("-d", "--debug", action = "store_true", help = "打印调试信息")
	parser.add_argument("-v", "--verbose", action = "store_true", help = "记录详细信息")
	group = parser.add_mutually_exclusive_group(required = True)
	group.add_argument("--assured", action = "store_true", help = "测试 assured-events.json 文件")
	group.add_argument("--findasession", action = "store_true", help = "测试 findasession.json 文件")
	group.add_argument("--saved", action = "store_true", help = "测试 savedEvent.json 文件")
	args = parser.parse_args()
	level = logging.DEBUG if args.verbose else logging.INFO
	setLogger(level, __file__, base_name = True, force_print = args.debug)
	asyncio.run(main(args))