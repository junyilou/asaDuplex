import asyncio
import json
import logging
from collections.abc import (AsyncGenerator, Callable, Coroutine,
                             Iterable, Mapping, Sequence)
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Concatenate, Literal, overload

import aiohttp
from tenacity import AsyncRetrying, stop_after_attempt, wait_fixed

type SemaphoreType = asyncio.Semaphore
type SessionType = aiohttp.ClientSession
type CoroutineType[T] = Coroutine[None, None, T]

browser_agent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
	"AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"}
request_logger = logging.getLogger("util.request")

async def _Container[T](*coros: CoroutineType[T] | Iterable[CoroutineType[T]],
	limit: int | None = None, return_exceptions: bool = False) -> list[asyncio.Task[T]]:
	from typing import TypeIs
	def iscoroutine(obj: Any) -> TypeIs[CoroutineType[Any]]:
		from inspect import iscoroutinefunction
		return iscoroutinefunction(obj)
	async def task(coro: CoroutineType[T],
		semaphore: SemaphoreType | None = None) -> T:
		async with with_semaphore(semaphore):
			try:
				return await coro
			except Exception as exp:
				if not return_exceptions:
					raise
				raise asyncio.CancelledError(exp)
	tasks: list[asyncio.Task] = []
	semaphore = asyncio.Semaphore(limit) if limit else None
	try:
		async with asyncio.TaskGroup() as tg:
			for gen in coros:
				if iscoroutine(gen):
					gen = gen,
				for coro in gen:
					tasks.append(tg.create_task(task(coro, semaphore)))
	except ExceptionGroup:
		pass
	return tasks

@overload
async def AsyncGather[T](*coros: CoroutineType[T] | Iterable[CoroutineType[T]],
	limit: int | None = None, return_exceptions: Literal[False] = False) -> list[T]: ...
@overload
async def AsyncGather[T](*coros: CoroutineType[T] | Iterable[CoroutineType[T]],
	limit: int | None = None, return_exceptions: Literal[True] = True) -> list[T | Exception]: ...
async def AsyncGather[T](*coros: CoroutineType[T] | Iterable[CoroutineType[T]],
	limit: int | None = None, return_exceptions: bool = False) -> list[T] | list[T | Exception]:
	results: list[Any] = []
	tasks = await _Container(*coros, limit = limit, return_exceptions = return_exceptions)
	for task in tasks:
		try:
			results.append(task.result())
		except asyncio.CancelledError as ce:
			if return_exceptions:
				results.append(ce.args[0])
			else:
				if ce.args:
					raise ce.args[0] from None
				raise ce from None
		except Exception as exp:
			if not return_exceptions:
				raise exp from None
	return results

async def _base_request(session: SessionType, url: str, method: str, modes: set[str], **kwargs) -> Any:
	results = {}
	async with session.request(url = url, method = method, **kwargs) as resp:
		for m in modes:
			d = ("head" if method == "HEAD" else "text") if m == "default" else m
			if d == "text":
				results[m] = await resp.text()
			elif d == "head":
				results[m] = resp.headers
			elif d == "cookies":
				results[m] = resp.cookies
			elif d == "status":
				results[m] = resp.status
			elif d == "json":
				results[m] = json.loads(await resp.text())
			elif d == "raw":
				results[m] = await resp.read()
		request_logger.debug(f"网络请求: [状态={resp.status}] [方法={method}] [URL={url}]")
	if len(modes) == 1:
		return results[modes.pop()]
	return results

def disMarkdown(text: str, *, wrap: str = "", extra: str = "", remove: str = "") -> str:
	signs = "\\|_{}[]()#@+-.!=<>~`" + extra
	text = text.translate({ord(s): f"\\{s}" for s in signs if s not in remove})
	return wrap + text + wrap[::-1]

@asynccontextmanager
async def get_session(
	session: SessionType | None = None,
	**kwargs) -> AsyncGenerator[SessionType]:
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

async def request(url: str, session: SessionType | None = None, method: str = "GET", *,
	mode: str | list[str] | None = None, retry: int = 1, sleep: int = 0,
	return_exception: bool = False, **kwargs) -> Any:
	modes = {str(i) for i in (mode if isinstance(mode, list) else [mode or "default"])}

	async def _request_impl(ses: SessionType) -> Any:
		return await _base_request(ses, url, method.upper(), modes, **kwargs)

	def log_retry(retry_state) -> None:
		if retry_state.outcome and retry_state.outcome.failed:
			request_logger.debug(f"等待重试: [方法={method}] [模式={mode}] [URL={url}]")

	try:
		async with get_session(session) as ses:
			retryer = AsyncRetrying(stop = stop_after_attempt(retry),
				wait = wait_fixed(sleep), after = log_retry, reraise = True)
			return await retryer(_request_impl, ses)
	except Exception as exp:
		request_logger.debug(f"异常丢弃: [方法={method}] [模式={mode}] [URL={url}]")
		if return_exception:
			return exp
		raise

def session_func[R, **P](func: Callable[Concatenate[SessionType, P],
	CoroutineType[R]]) -> Callable[P, CoroutineType[R]]:
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

def sortOD[K, V](od: Mapping[K, V], reverse: Sequence[bool] = (False,),
	key: Callable[[tuple[K, V]], Any] | None = None, level: int = 0) -> dict[K, V]:
	res: dict[K, V] = {}
	rev = reverse[min(level, len(reverse) - 1)]
	sorted_items = sorted(od.items(), reverse=rev, key=key)
	for k, v in sorted_items:
		match v:
			case Mapping():
				res[k] = sortOD(v, reverse=reverse, key=key, level=level + 1)  # type: ignore
			case list():
				res[k] = sorted(v)  # type: ignore
			case _:
				res[k] = v
	return res

def tz_text(dtime: datetime) -> str:
	delta = (dtime.utcoffset() or timedelta()).total_seconds() / 3600
	time_h = delta - (time_min := delta % 1)
	return f"GMT{time_h:+.0f}{f":{60 * time_min:0>2.0f}" if time_min else ""}"

@asynccontextmanager
async def with_semaphore(semaphore: SemaphoreType | None = None) -> AsyncGenerator[None]:
	try:
		if semaphore:
			await semaphore.acquire()
		yield
	finally:
		if semaphore:
			semaphore.release()
