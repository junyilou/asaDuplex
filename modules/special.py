import logging
import aiohttp
import json
from datetime import timedelta, date, datetime
from storeInfo import storeInfo, storeDict
from modules.constants import request as request
from modules.constants import userAgent, dayOfWeekENG, partSample, storeNation

def textConvert(strdict):
	if strdict["closed"]:
		return "不营业"
	elif strdict["openTime"] == "00:00" and strdict["closeTime"] == "23:59":
		return "24 小时营业"
	else:
		return f'{strdict["openTime"]} - {strdict["closeTime"]}'

async def comment(session, sid, sif = None):
	try:
		sif = storeInfo(sid) if sif == None else sif
		partNumber = f"MM0A3{partSample[sif['flag']]}/A"
	except KeyError:
		return {}

	baseURL = f"https://www.apple.com{storeNation[sif['flag']]}"
	referer = {**userAgent, "Referer": f"{baseURL}/shop/product/{partNumber}"}
	url = f"{baseURL}/shop/fulfillment-messages?searchNearby=true&parts.0={partNumber}&store=R{sid}"

	try:
		r = await request(session = session, url = url, headers = userAgent, ident = None, ensureAns = False)
		j = json.loads(r)["body"]["content"]["pickupMessage"]["stores"]
	except:
		return {}

	reason = {}
	for s in j:
		if s["storeNumber"] != f"R{sid}":
			continue
		for h in s["retailStore"]["storeHolidays"]:
			sDay = datetime.strptime(h["date"], "%b %d")
			sDay = date(date.today().year, sDay.month, sDay.day)
			sTxt = (f"[{h['description']}]" if h["description"] else "") + (f" {h['comments']}" if h["comments"] else "")
			reason[sDay] = sTxt
	return reason

async def speHours(session, sid, limit = 14):
	sif = storeInfo(sid)
	try:
		j = await storeDict(session = session, mode = "hours", sif = sif)
		if not j:
			raise ValueError()
	except:
		logging.getLogger("special").error(f"未能获得 R{sid} 营业时间信息")
		return {}
	if not j:
		return {}

	regularHours = {}
	for regular in j["regular"]:
		dayIndex = dayOfWeekENG.index(regular["name"])
		regularHours[dayIndex] = textConvert(regular)
	
	specialHours = {}
	specialToday = date.today()
	if j["special"]:
		specialReasons = await comment(session = session, sid = sid, sif = sif)
	j["special"].sort(key = lambda k: k["date"])
	for special in j["special"]:
		if len(specialHours) == limit:
			break

		validDate = datetime.strptime(special["date"], "%Y-%m-%d").date()
		regular = regularHours[validDate.weekday()]
		spetext = textConvert(special)

		if validDate < specialToday:# or regular == spetext:
			continue
		if validDate in specialReasons:
			reason = {"reason": specialReasons[validDate]}
		else:
			reason = {}
		
		regular = regularHours[validDate.weekday()]
		specialHours[str(validDate)] = {"regular": regular, "special": spetext, **reason}
	specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))
	return specialHours