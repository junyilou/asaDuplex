import logging
import asyncio
from random import choice
from datetime import timedelta, datetime
from storeInfo import StoreID, Store
from modules.constants import allRegions, userAgent
from modules.util import request

COMMENTS = {}
SLEEPER = list(range(2, 16, 2))
dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def textConvert(dct, userLang = True):
	match dct:
		case {"closed": True}:
			return "不营业" if userLang else "Closed"
		case {"openTime": "00:00", "closeTime": "23:59"}:
			return "24 小时营业" if userLang else "Always Open"
		case {"openTime": opt, "closeTime": clt}:
			return f'{opt} - {clt}'
	return "未知时间" if userLang else "Unknown Hours"

async def apu(session, store: Store, target, userLang):
	retry = 3
	baseURL = f"https://www.apple.com{store.region['shopURL']}"
	url = f"{baseURL}/shop/fulfillment-messages"
	referer = userAgent | {"Referer": f"{baseURL}/shop/product/{target}"}	
	params = {"searchNearby": "true", "store": store.rid, "parts.0": target}

	stores = []
	while retry:
		try:
			r = await request(session = session, url = url, headers = referer, 
				params = params, ensureAns = False, raise_for_status = True, mode = "json")
			stores = r["body"]["content"]["pickupMessage"]["stores"]
			break
		except:
			retry -= 1
			logging.debug(("等待 {SEC} 秒" if userLang else "Wait for {SEC} sec").format(SEC = (sec := choice(SLEEPER))))
			await asyncio.sleep(sec)

	for store in stores:
		astore = store["storeNumber"].removeprefix("R")
		for ind, holiday in enumerate(store["retailStore"]["storeHolidays"]):
			sDay = datetime.strptime(f'2000 {holiday["date"]}', "%Y %b %d").date()
			cDay = datetime(2000, (today := datetime.now().today()).month, today.day).date() - timedelta(weeks = 1)
			sYear = today.year if sDay >= cDay else today.year + 1
			sDay = datetime(sYear, sDay.month, sDay.day).date()
			sTxt = (f"[{holiday['description']}]" if holiday["description"] else "") + (f" {holiday['comments']}" if holiday["comments"] else "")
			yield (astore, sDay, sTxt)

async def comment(session, store: Store, userLang = True):
	global COMMENTS
	async for i in apu(session, store, f'MM0A3{store.region["partSample"]}/A', userLang):
		astore, sDay, sTxt = i
		COMMENTS[astore] = COMMENTS.get(astore, {})
		COMMENTS[astore][sDay] = sTxt
	return COMMENTS

async def speHours(sid, session = None, runtime = None, limit = 14, askComment = True, userLang = True):
	store = StoreID(sid)[0]
	runtime = datetime.now().date() if runtime is None else runtime
	try:
		j = await store.detail(session = session, mode = "hours")
		assert j
	except:
		logging.getLogger(__name__).error(f"未能获得 {store.rid} 营业时间信息" if userLang else f"Failed getting store hours for {store.rid}")
		return []

	regularHours = {}
	for regular in j["regular"]:
		dayIndex = dayOfWeek.index(regular["name"])
		regularHours[dayIndex] = textConvert(regular, userLang = userLang)
	
	specialHours, specialReasons = {}, {}
	if j["special"] and askComment:
		specialReasons = await comment(session = session, store = store, userLang = userLang)
	for special in sorted(j["special"], key = lambda k: k["date"]):
		if len(specialHours) >= limit:
			break
		validDate = datetime.strptime(special["date"], "%Y-%m-%d").date()
		if validDate < runtime:
			continue
		regular = regularHours[validDate.weekday()]
		spetext = textConvert(special, userLang = userLang)
		comm = {"comment": specialReasons[store.sid][validDate]} if validDate in specialReasons.get(store.sid, {}) else {}
		specialHours[str(validDate)] = {"regular": regular, "special": spetext} | comm
	specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))
	return specialHours