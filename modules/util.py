import aiohttp
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Coroutine
from datetime import datetime, timedelta
from functools import wraps
from os.path import basename, isdir
from typing import Any, Concatenate, Optional

type SemaphoreType = asyncio.Semaphore
type SessionType = aiohttp.ClientSession

def bitsize(integer: int | float, width: int = 8, precision: int = 2, ks: float = 1e3) -> str:
	unit, order = 0, ["B", "KB", "MB", "GB", "TB"]
	while integer > ks and unit < len(order) - 1:
		integer /= ks
		unit += 1
	return f"{integer:{width}.{precision}f} {order[unit]:<2}"

def disMarkdown(text: str, wrap: str = "", extra: str = "") -> str:
	temp = str(text)
	signs = "\\|_{}[]()#@+-.!=<>~" + extra
	for s in signs:
		temp = temp.replace(s, "\\" + s)
	return wrap + temp + wrap[::-1]

def sortOD(od: dict, reverse: list[bool] = [False], key: Optional[Callable] = None, level: int = 0) -> dict:
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

def timeDelta(*, seconds: float = 0, dt1: datetime = datetime.min, dt2: datetime = datetime.min,
	items: Optional[int] = None, empty: str = "") -> str:
	ans, base = [], 1
	comp = [(60, "秒"), (60, "分钟"), (24, "小时"), (7, "天"), (0, "周")]
	s = int(abs(seconds or (dt2 - dt1).total_seconds()))
	if not s:
		return empty
	items = items or len(comp)
	for carry, desc in comp:
		if (c := s // base):
			if (l := f"{c % carry if carry else c:.0f}") != "0":
				ans.append(f"{l} {desc}")
		base *= carry
		if s < base:
			break
	return " ".join(ans[-1:-1-items:-1])

def timezoneText(dtime: datetime) -> str:
	delta = (dtime.utcoffset() or timedelta()).total_seconds() / 3600
	time_min = delta % 1
	time_h = delta - time_min
	return f"GMT{time_h:+.0f}" + (f":{60 * time_min:0>2.0f}" if time_min else "")

async def request(session: Optional[SessionType] = None,
	url: str = "", method: str = "GET", mode: str | list[str] = ["text"],
	retryNum: int = 1, ensureAns: bool = True, **kwargs) -> Any:
	assert url, "URL 不正确"
	logger = logging.getLogger("util.request")

	close_session = False
	if session is None:
		logger.debug("已创建新的 aiohttp 线程")
		session = aiohttp.ClientSession()
		close_session = True

	modes: list[str] = mode if isinstance(mode, list) else [mode]
	logger.debug(", ".join(f"[{k}] {v}" for k, v in {method: repr(url), "模式": mode, "参数": kwargs, "重试": retryNum}.items()))
	while retryNum:
		try:
			async with session.request(url = url, method = method, **kwargs) as resp:
				results = {}
				for m in set(modes):
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
			logger.debug(", ".join(f"[{k}] {v}" for k, v in {f"状态{resp.status}": repr(url)}.items()))
			if close_session:
				await session.close()
			if len(modes) == 1:
				return next(iter(results.values()))
			return results
		except Exception as exp:
			retryNum -= 1
			if retryNum <= 0:
				logger.debug(", ".join(f"[{k}] {v}" for k, v in {"丢弃": repr(url), "异常": repr(exp)}.items()))
				if close_session:
					await session.close()
				if ensureAns:
					return exp
				raise exp
			logger.debug(", ".join(f"[{k}] {v}" for k, v in {"丢弃": repr(url), "异常": repr(exp), "重试剩余": retryNum}.items()))

def session_func[Y, S, R, **P](func: Callable[Concatenate[SessionType, P],
	Coroutine[Y, S, R]]) -> Callable[P, Coroutine[Y, S, R]]:
	@wraps(func)
	async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
		async with aiohttp.ClientSession() as session:
			return await func(session, *args, **kwargs)
	return wrapper

def sync(coroutine: Optional[Awaitable] = None, loop: Optional[asyncio.AbstractEventLoop] = None) -> Any:
	if loop is None:
		loop = asyncio.new_event_loop()
	if coroutine is not None:
		return loop.run_until_complete(coroutine)
	return loop

def setLogger(level: int, name: str, *, base_name: bool = False, force_print: bool = False) -> None:
	if base_name:
		name = basename(name)
	if isdir('logs') and not force_print:
		return logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	return logging.basicConfig(
		format = '[%(process)d %(asctime)s %(name)s %(levelname)s] %(message)s',
		level = level, datefmt = '%T')