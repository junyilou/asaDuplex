import os
import json
import logging
import asyncio
import aiohttp

def disMarkdown(text):
	temp = text
	signs = "\\|_{}[]()#+-.!=<>~"
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return temp

def timezoneText(dtime):
	delta = dtime.utcoffset().total_seconds() / 3600
	dx, dy = str(delta).split(".")
	if dy == "0":
		tzText = f"GMT{int(dx):+}"
	else:
		tzText = f"GMT{int(dx):+}:{60 * float('.' + dy):0>2.0f}"
	return tzText

async def request(session = None, url = None, ident = None, mode = None, retryNum = 1, ensureAns = True, **kwargs):
	method = kwargs.get("method", "GET")
	pop = kwargs.pop("method") if "method" in kwargs else None

	close_session = False
	if session == None:
		logging.getLogger("constants.request").debug("Created new Session")
		session = aiohttp.ClientSession()
		close_session = True

	logging.getLogger("constants.request").debug(f"[{'MTH ' + method:^9}] '{url}', [ident] {ident}, [mode] {mode}, [args] {kwargs}, [retry] {retryNum}")
	while retryNum:
		try:
			async with session.request(url = url, method = method, **kwargs) as resp:
				if mode == "raw":
					r = await resp.read()
				elif mode == "head":
					r = resp.headers
				elif mode == "status":
					r = resp.status
				elif mode == "json":
					try:
						r = await resp.json()
					except:
						r = await resp.text()
						r = json.loads(r)
				else:
					r = await resp.text()
			logging.getLogger("constants.request").debug(f"[Status {resp.status}] '{url}'")
			if close_session:
				await session.close()
			return (r, ident) if ident else r
		except Exception as exp:
			if retryNum == 1:
				logging.getLogger("constants.request").debug(f"[Abandoned] '{url}', [ident] {ident}, [exp] {exp}")
				if close_session:
					await session.close()
				if ensureAns:
					return (exp, ident) if ident else exp
				else:
					raise exp
			else:
				retryNum -= 1
				logging.getLogger("constants.request").debug(f"[Exception] '{url}', [ident] {ident}, [exp] {exp}, [retry] {retryNum} left")

def session_func(func, **kwargs):
	async def wrapper(**kwargs):
		async with aiohttp.ClientSession() as session:
			return await func(session = session, **kwargs)
	return wrapper

def sync(coroutine = None, loop = None):
	if loop == None:
		loop = asyncio.new_event_loop()
	if coroutine != None:
		return loop.run_until_complete(coroutine)
	else:
		return loop

def setLogger(level, name):
	if os.path.isdir('logs'):
		logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	else:
		logging.basicConfig(
			format = '[%(process)d %(asctime)s %(name)s %(levelname)s] %(message)s',
			level = level, datefmt = '%T')