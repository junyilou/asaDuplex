import json
import logging
import asyncio
import aiohttp
from os.path import isdir

def disMarkdown(text, wrap = "", extra = ""):
	temp = text
	signs = "\\|_{}[]()#@+-.!=<>~" + extra
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return wrap + temp + wrap[::-1]

def timezoneText(dtime):
	delta = dtime.utcoffset().total_seconds() / 3600
	dx, dy = str(delta).split(".")
	if dy == "0":
		tzText = f"GMT{int(dx):+}"
	else:
		tzText = f"GMT{int(dx):+}:{60 * float('.' + dy):0>2.0f}"
	return tzText

def bitsize(integer, width = 8, precision = 2, ks = 1e3):
	order = [" B", "KB", "MB", "GB", "TB"]
	unit = 0
	while integer > ks and unit < len(order) - 1:
		integer /= ks
		unit += 1
	return f"{integer:{width}.{precision}f} {order[unit]}"

def sortOD(od, reverse = [False], key = None, level = 0):
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

async def request(session = None, url = None, mode = None, retryNum = 1, ensureAns = True, **kwargs):
	method = kwargs.get("method", "GET")
	pop = kwargs.pop("method") if "method" in kwargs else None
	logger = logging.getLogger("async_request")

	close_session = False
	if session == None:
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

def sync(coroutine = None, loop = None):
	if loop == None:
		loop = asyncio.new_event_loop()
	if coroutine != None:
		return loop.run_until_complete(coroutine)
	else:
		return loop

def setLogger(level, name, force_print = False):
	if isdir('logs') and not force_print:
		logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	else:
		logging.basicConfig(
			format = '[%(process)d %(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, datefmt = '%T')