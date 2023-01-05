import aiohttp
import asyncio
import json
import logging
from datetime import datetime
from typing import Callable, Awaitable
from os.path import isdir

def bitsize(integer: int | float, width: int = 8, precision: int = 2, ks: float = 1e3) -> str:
	order = [" B", "KB", "MB", "GB", "TB"]
	unit = 0
	while integer > ks and unit < len(order) - 1:
		integer /= ks
		unit += 1
	return f"{integer:{width}.{precision}f} {order[unit]}"

def disMarkdown(text: str, wrap: str = "", extra: str = "") -> str:
	temp = str(text)
	signs = "\\|_{}[]()#@+-.!=<>~" + extra
	for s in signs:
		temp = temp.replace(s, "\\" + s)
	return wrap + temp + wrap[::-1]

def sortOD(od: dict, reverse: list[bool] = [False], key: Callable = None, level: int = 0) -> dict:
	res = {}
	for k, v in sorted(od.items(), reverse = reverse[min(level, len(reverse) - 1)], key = key):
		match v:
			case dict():
				res[k] = sortOD(v, reverse = reverse, key = key, level = level + 1)
			case list():
				res[k] = sorted(v)
			case _:
				res[k] = v
	return res

def timezoneText(dtime: datetime) -> str:
	delta = dtime.utcoffset().total_seconds() / 3600
	dx, dy = str(delta).split(".")
	return f"GMT{int(dx):+}" + (f":{60 * float('.' + dy):0>2.0f}" if dy != "0" else "")

async def request(session: aiohttp.ClientSession = None, url: str = None, mode: str | list[str] = None, 
	retryNum: int = 1, ensureAns: bool = True, **kwargs) -> int | str | dict | bytes | Exception:
	method = kwargs.get("method", "GET")
	pop = kwargs.pop("method") if "method" in kwargs else None
	logger = logging.getLogger("async_request")

	close_session = False
	if session is None:
		logger.debug("已创建新的 aiohttp 线程")
		session = aiohttp.ClientSession()
		close_session = True

	mode = [mode] if type(mode) != list else mode
	logger.debug(f"[{method}] '{url}', [模式] {mode}, [参数] {kwargs}, [重试] {retryNum}")
	while retryNum:
		try:
			async with session.request(url = url, method = method, **kwargs) as resp:
				results = {}
				for m in mode:
					match m:
						case "raw":
							results[m] = await resp.read()
						case "head":
							results[m] = resp.headers
						case "status":
							results[m] = resp.status
						case "json":
							try:
								results[m] = await resp.json()
							except:
								r = await resp.text()
								results[m] = json.loads(r)
						case _:
							results[m] = await resp.text()
			logger.debug(f"[状态{resp.status}] '{url}'")
			if close_session:
				await session.close()
			if len(mode) == 1:
				return results[mode[0]]
			return results
		except Exception as exp:
			if retryNum == 1:
				logger.debug(f"[丢弃] '{url}', [异常] {exp}")
				logger.debug(exp.__repr__())
				if close_session:
					await session.close()
				if ensureAns:
					return exp
				raise exp
			else:
				retryNum -= 1
				logger.debug(f"[异常] '{url}', [异常] {exp}, [重试剩余] {retryNum}")
				logger.debug(exp.__repr__())

def session_func(func):
	async def wrapper(*args, **kwargs):
		async with aiohttp.ClientSession() as session:
			return await func(session = session, *args, **kwargs)
	return wrapper

def sync(coroutine: Awaitable = None, loop: asyncio.AbstractEventLoop = None):
	if loop is None:
		loop = asyncio.new_event_loop()
	if coroutine is not None:
		return loop.run_until_complete(coroutine)
	return loop

def setLogger(level: int, name: str, force_print: bool = False):
	if isdir('logs') and not force_print:
		logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	else:
		logging.basicConfig(
			format = '[%(process)d %(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, datefmt = '%T')