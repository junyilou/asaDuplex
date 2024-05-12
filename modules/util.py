import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Concatenate, Mapping, Optional

import aiohttp

type SemaphoreType = asyncio.Semaphore
type SessionType = aiohttp.ClientSession

browser_agent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"}
request_logger = logging.getLogger("util.request")

def bitsize(integer: int | float, width: int = 8, precision: int = 2, ks: float = 1e3) -> str:
	unit, order = 0, ("B", "KB", "MB", "GB", "TB")
	while integer > ks and unit < len(order) - 1:
		integer /= ks
		unit += 1
	return f"{integer:{width}.{precision}f} {order[unit]:<2}"

def disMarkdown(text: str, wrap: str = "", extra: str = "") -> str:
	signs = "\\|_{}[]()#@+-.!=<>~" + extra
	text = text.translate({ord(s): f"\\{s}" for s in signs})
	return wrap + text + wrap[::-1]

def sortOD[K, V](od: Mapping[K, V],
	reverse: list[bool] = [False],
	key: Optional[Callable[..., Any]] = None,
	level: int = 0) -> dict[K, V]:
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

def timeDelta(*,
	seconds: float = 0,
	dt1: datetime = datetime.min,
	dt2: datetime = datetime.min,
	items: Optional[int] = None,
	empty: str = "") -> str:
	ans, base = [], 1
	comp = ((60, "秒"), (60, "分钟"), (24, "小时"), (7, "天"), (0, "周"))
	s = int(abs(seconds or (dt2 - dt1).total_seconds()))
	if not s:
		return empty
	items = items or len(comp)
	for carry, desc in comp:
		if c := s // base:
			if (l := f"{c % carry if carry else c:.0f}") != "0":
				ans.append(f"{l} {desc}")
		base *= carry
		if s < base:
			break
	return " ".join(ans[-1:-1-items:-1])

def tz_text(dtime: datetime) -> str:
	delta = (dtime.utcoffset() or timedelta()).total_seconds() / 3600
	time_h = delta - (time_min := delta % 1)
	return f"GMT{time_h:+.0f}{f":{60 * time_min:0>2.0f}" if time_min else ""}"

async def base_request(
	url: str,
	method: str,
	session: SessionType,
	modes: set[str],
	**kwargs) -> Any:
	results = {}
	async with session.request(url = url, method = method, **kwargs) as resp:
		for m in modes:
			d = ("head" if method == "HEAD" else "text") if m == "default" else m
			if d == "text":
				results[m] = await resp.text()
			elif d == "head":
				results[m] = resp.headers
			elif d == "status":
				results[m] = resp.status
			elif d == "json":
				results[m] = json.loads(await resp.text())
			elif d == "raw":
				results[m] = await resp.read()
			elif d == "blank":
				results[m] = None
		request_logger.debug(f"网络请求: [状态={resp.status}] [方法={method}] [URL={url}]")
	if len(modes) == 1:
		return results[modes.pop()]
	return results

@asynccontextmanager
async def get_session(
	session: Optional[SessionType] = None,
	**kwargs) -> AsyncIterator[SessionType]:
	y = session or aiohttp.ClientSession(**kwargs)
	i = y is not session
	if i:
		request_logger.debug("已创建新的 aiohttp 线程")
	try:
		yield y
	finally:
		if i:
			await y.close()
			request_logger.debug("已关闭临时 aiohttp 线程")

@asynccontextmanager
async def with_semaphore(
	semaphore: Optional[SemaphoreType] = None) -> AsyncIterator[None]:
	try:
		if semaphore:
			await semaphore.acquire()
		yield
	finally:
		if semaphore:
			semaphore.release()

async def request(
	url: str,
	session: Optional[SessionType] = None,
	method: str = "GET", *,
	mode: Optional[str | list[str]] = None,
	retry: int = 1,
	return_exception: bool = False,
	**kwargs) -> Any:
	modes = {str(i) for i in (mode if isinstance(mode, list) else [mode or "default"])}
	while retry:
		retry -= 1
		async with get_session(session) as ses:
			try:
				return await base_request(url, method.upper(), ses, modes, **kwargs)
			except Exception as exp:
				if not retry:
					request_logger.debug(f"异常丢弃: [方法={method}] [模式={mode}] [URL={url}]")
					if return_exception:
						return exp
					raise
		request_logger.debug(f"等待重试: [方法={method}] [模式={mode}] [URL={url}] [重试剩余={retry}]")

def session_func[R, **P](
	func: Callable[Concatenate[SessionType, P],
	Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
	from functools import wraps
	@wraps(func)
	async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
		async with aiohttp.ClientSession() as session:
			return await func(session, *args, **kwargs)
	return wrapper

def setLogger(
	level: int,
	name: str, *,
	base_name: bool = False,
	force_print: bool = False) -> None:
	from os.path import basename, isdir
	if base_name:
		name = basename(name)
	if isdir("logs") and not force_print:
		return logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	return logging.basicConfig(
		format = '[%(process)d %(asctime)s %(name)s %(levelname)s] %(message)s',
		level = level, datefmt = '%T')