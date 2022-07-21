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

asaVersion = "5.16.0"
asaAgent = ".".join(asaVersion.split(".")[:2])
asaHeaders = {
	"User-Agent": f"ASA/{asaAgent} (iPhone) ss/3.00",
	"x-ma-pcmh":  f"REL-{asaVersion}",
	"X-MALang":   "zh-CN",
	"X-Apple-I-TimeZone": "GMT+8",
	"X-Apple-I-Locale":   "zh_CN",
	"X-MMe-Client-Info": f"<iPhone13,2> <iPhone OS;15.5;19F77> <com.apple.AuthKit/1 (com.apple.store.Jolly/{asaVersion})>",
	"X-DeviceConfiguration":  f"ss=3.00;dim=1170x2532;m=iPhone;v=iPhone13,2;vv={asaAgent};sv=15.5"}
asaNation = {'🇺🇸': 'a/us', '🇨🇳': 'p/cn', '🇬🇧': 'e/uk', '🇨🇦': 'a/ca', '🇦🇺': 'p/au', '🇫🇷': 'e/fr', 
	'🇮🇹': 'e/it', '🇩🇪': 'e/de', '🇪🇸': 'e/es', '🇯🇵': 'j/jp', '🇨🇭': 'e/ch-de', '🇦🇪': 'e/ae', '🇳🇱': 'e/nl', 
	'🇸🇪': 'e/se', '🇧🇷': 'a/br', '🇹🇷': 'e/tr', '🇸🇬': 'p/sg', '🇲🇽': 'a/mx', '🇦🇹': 'e/at', '🇧🇪': 'e/be-fr', 
	'🇰🇷': 'p/kr', '🇹🇭': 'p/th-en', '🇭🇰': 'p/hk-zh', '🇹🇼': 'p/tw'} # No Service in Macau and India

userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"}

webNation = {**dict([(i[0], i[1][1:4]) for i in asaNation.items()]), 
	"🇺🇸": '', "🇨🇳": '.cn', "🇨🇭": "/chde", "🇧🇪": "/befr", "TW": "/tw", '🇲🇴': '/mo', '🇮🇳': '/in'} # for /retail
storeNation = {**webNation, "🇨🇭": "/ch-de", "🇧🇪": "/be-fr"} # for /shop
todayNation = {**{v: k for k, v in webNation.items()}, "/cn": "🇨🇳", "/tw": "🇹🇼"} # for /today-bff
localeNation = {'🇺🇸': 'en_US', '🇨🇳': 'zh_CN', '🇬🇧': 'en_GB', '🇨🇦': 'en_CA', '🇦🇺': 'en_AU', '🇫🇷': 'fr_FR', 
	'🇮🇹': 'it_IT', '🇩🇪': 'de_DE', '🇪🇸': 'es_ES', '🇯🇵': 'ja_JP', '🇨🇭': 'de_CH', '🇦🇪': 'en_AE', '🇳🇱': 'nl_NL', 
	'🇸🇪': 'sv_SE', '🇧🇷': 'pt_BR', '🇹🇷': 'tr_TR', '🇸🇬': 'en_SG', '🇲🇽': 'es_MX', '🇦🇹': 'de_AT', '🇧🇪': 'fr_BE', 
	'🇰🇷': 'ko_KR', '🇹🇭': 'th_TH', '🇭🇰': 'zh_HK', '🇲🇴': 'zh_MO', '🇹🇼': 'zh_TW', '🇮🇳': 'en_IN'} # for rsp

partSample = {'🇺🇸': 'AM', '🇨🇳': 'FE', '🇬🇧': 'ZM', '🇨🇦': 'AM', '🇦🇺': 'FE', '🇫🇷': 'ZM', 
	'🇮🇹': 'ZM', '🇩🇪': 'ZM', '🇪🇸': 'ZM', '🇯🇵': 'FE', '🇳🇱': 'ZM', 
	'🇸🇪': 'ZM', '🇸🇬': 'FE', '🇦🇹': 'ZM', 
	'🇰🇷': 'FE', '🇹🇭': 'FE', '🇭🇰': 'FE', '🇹🇼': 'FE', '🇮🇳': 'ZM'} # for fulfillment-messages

partRuleBase = r"[FGHMNPS][0-9A-Z]{3}[0-9]"
partRuleFull = r".*([FGHMNPS][0-9A-Z]{3}[0-9][A-Z]{1,2}/[A-Z]).*"
partRuleCheck = r".*([FGHMNPS][0-9A-Z]{3}[0-9]([A-Z]{1,2}/[A-Z])?).*"
partSpecialProduct = r".*(Z[0-9A-Z]{3}&(.*)?).*"

DIFFhead = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIFF HEAD</title>
</head>

<body><pre><code>\n"""
DIFFfoot = "</code></pre></body></html>"

editStart = "### *** EDIT START *** ###\n"
editEnd   = "\n### *** EDIT  END  *** ###"

RecruitDict = {
	"🇹🇷": {"name": "土耳其", "code": 114438164, "altername": ["Turkey", "TR", "Türkiye"]}, 
	"🇦🇪": {"name": "阿联酋", "code": 114438225, "altername": ["United Arab Emirates", "UAE", "AE", "阿拉伯联合酋长国", "阿拉伯联合大公国"]}, 
	"🇬🇧": {"name": "英国", "code": 114438145, "altername": ["United Kingdom", "UK", "GB", "Great Britain"]}, 
	"🇩🇪": {"name": "德国", "code": 114438043, "altername": ["Germany", "DE", "Deutschland"]}, 
	"🇹🇼": {"name": "台湾", "code": 114438311, "altername": ["Taiwan", "TW", "ROC"]}, 
	"🇺🇸": {"name": "美国", "code": 114438158, "altername": ["United States", "US", "America"]}, 
	"🇲🇽": {"name": "墨西哥", "code": 114438297, "altername": ["Mexico", "MX"]}, 
	"🇨🇭": {"name": "瑞士", "code": 114438017, "altername": ["Switzerland", "CH", "Swiss"]}, 
	"🇧🇪": {"name": "比利时", "code": 114438251, "altername": ["Belgium", "BE"]}, 
	"🇳🇱": {"name": "荷兰", "code": 114438119, "altername": ["Netherlands", "Holland", "NL"]}, 
	"🇪🇸": {"name": "西班牙", "code": 114438056, "altername": ["Spain", "ES", "España"]}, 
	"🇭🇰": {"name": "香港", "code": 114438082, "altername": ["Hong Kong", "HK"]}, 
	"🇸🇪": {"name": "瑞典", "code": 114438132, "altername": ["Sweden", "SE"]}, 
	"🇨🇳": {"name": "中国", "code": 114438030, "altername": ["China", "CN", "PRC"]}, 
	"🇫🇷": {"name": "法国", "code": 114438069, "altername": ["France", "FR"]}, 
	"🇦🇺": {"name": "澳大利亚", "code": 114437991, "altername": ["Australia", "AU", "澳洲"]}, 
	"🇮🇹": {"name": "意大利", "code": 114438095, "altername": ["Italy", "IT", "Italia", "义大利"]}, 
	"🇲🇴": {"name": "澳门", "code": 114438282, "altername": ["Macau", "MO", "Macao"]}, 
	"🇧🇷": {"name": "巴西", "code": 114438176, "altername": ["Brazil", "BR"]}, 
	"🇯🇵": {"name": "日本", "code": 114438107, "altername": ["Japan", "JP"]}, 
	"🇰🇷": {"name": "韩国", "code": 114438326, "altername": ["South Korea", "KR", "ROK", "南韩", "大韩民国"]}, 
	"🇨🇦": {"name": "加拿大", "code": 114438004, "altername": ["Canada", "CA"]}, 
	"🇦🇹": {"name": "奥地利", "code": 114438333, "altername": ["Austria", "AT"]}, 
	"🇸🇬": {"name": "新加坡", "code": 114438238, "altername": ["Singapore", "SG", "星加坡"]},
	"🇹🇭": {"name": "泰国", "code": 114438346, "altername": ["Thailand", "TH"]},
	"🇮🇳": {"name": "印度", "code": 200314117, "altername": ["India", "IN"]}
}