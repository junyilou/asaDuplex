import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta
from modules.util import SessionType
from modules.util import browser_agent, request
from random import choice
from typing import Optional
from storeInfo import Store, getStore

COMMENTS: dict[str, dict[date, str]] = {}
SLEEPER = list(range(2, 16, 2))
dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def textConvert(dct: dict, userLang: bool = True) -> str:
	match dct:
		case {"closed": True}:
			return "不营业" if userLang else "Closed"
		case {"openTime": "00:00", "closeTime": "23:59"}:
			return "24 小时营业" if userLang else "Always Open"
		case {"openTime": opt, "closeTime": clt}:
			return f'{opt} - {clt}'
	return "未知时间" if userLang else "Unknown Hours"

async def apu(session: Optional[SessionType], store: Store, target: str, userLang: bool) -> AsyncIterator[tuple[str, date, str]]:
	retry = 3
	baseURL = f"https://www.apple.com{store.region.url_store}"
	url = f"{baseURL}/shop/fulfillment-messages"
	referer = browser_agent | {"Referer": f"{baseURL}/shop/product/{target}"}
	params = {"searchNearby": "true", "store": store.rid, "parts.0": target}

	stores: list[dict] = []
	while retry:
		try:
			r = await request(url, session, headers = referer, timeout = 5,
				params = params, raise_for_status = True, mode = "json")
			stores = r["body"]["content"]["pickupMessage"]["stores"]
			break
		except:
			retry -= 1
			sec = choice(SLEEPER)
			logging.debug(("等待 {SEC} 秒" if userLang else "Wait for {SEC} sec").format(SEC = sec))
			await asyncio.sleep(sec)

	for rstore in stores:
		astore = rstore["storeNumber"].removeprefix("R")
		for holiday in rstore["retailStore"]["storeHolidays"]:
			sDay = datetime.strptime(f'2000 {holiday["date"]}', "%Y %b %d").date()
			cDay = datetime(2000, (today := datetime.now().today()).month, today.day).date() - timedelta(weeks = 1)
			sYear = today.year if sDay >= cDay else today.year + 1
			sDay = datetime(sYear, sDay.month, sDay.day).date()
			sTxt = (f"[{holiday['description']}]" if holiday["description"] else "") + (f" {holiday['comments']}" if holiday["comments"] else "")
			yield (astore, sDay, sTxt)

async def comment(session: Optional[SessionType], store: Store, userLang: bool = True) -> dict:
	async for i in apu(session, store, f'MM0A3{store.region.part_sample}/A', userLang):
		astore, sDay, sTxt = i
		COMMENTS[astore] = COMMENTS.get(astore, {})
		COMMENTS[astore][sDay] = sTxt
	return COMMENTS

async def speHours(store: Store, session: Optional[SessionType] = None,
	runtime: Optional[date] = None, limit: int = 14, askComment: bool = True,
	userLang: bool = True) -> list | dict[str, dict[str, str]]:
	j = {}
	runtime = datetime.now().date() if runtime is None else runtime
	try:
		j = await store.detail(session = session, mode = "hours")
		assert isinstance(j, dict) and "regular" in j
	except AssertionError:
		logging.getLogger(__name__).error(f"[DEBUG] 远程数据无效: {j!r}")
		return []
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