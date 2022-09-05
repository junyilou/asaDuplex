import logging
import aiohttp
from datetime import timedelta, date, datetime
from storeInfo import storeInfo, storeDict, StoreID
from modules.constants import userAgent, allRegions
from modules.util import request

COMMENTS = {}
dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def textConvert(strdict, userLang = True):
	if strdict["closed"]:
		return "不营业" if userLang else "Closed"
	elif strdict["openTime"] == "00:00" and strdict["closeTime"] == "23:59":
		return "24 小时营业" if userLang else "Always Open"
	else:
		return f'{strdict["openTime"]} - {strdict["closeTime"]}'

async def comment(session, sid, sif = None):
	global COMMENTS

	sif = storeInfo(sid) if sif == None else sif
	sid = StoreID(sid)[0][0]
	partNumber = f'MM0A3{allRegions[sif["flag"]]["partSample"]}/A'
	baseURL = f"https://www.apple.com{allRegions[sif['flag']]['shopURL']}/shop"

	if allRegions[sif['flag']]['shopURL'] == None:
		return COMMENTS
	referer = {**userAgent, "Referer": f"{baseURL}/product/MM0A3"}
	url = f"{baseURL}/fulfillment-messages?searchNearby=true&parts.0={partNumber}&store=R{sid}"

	try:
		r = await request(session = session, url = url, headers = userAgent, 
			ident = None, ensureAns = False, mode = "json")
		j = r["body"]["content"]["pickupMessage"]["stores"]
	except:
		return COMMENTS

	for s in j:
		for h in s["retailStore"]["storeHolidays"]:
			aid = s["retailStore"]["storeNumber"].lstrip("R")
			sDay = datetime.strptime(h["date"], "%b %d")
			sDay = date(date.today().year, sDay.month, sDay.day)
			sTxt = (f"[{h['description']}]" if h["description"] else "") + (f" {h['comments']}" if h["comments"] else "")
			COMMENTS[aid] = COMMENTS.get(aid, {})
			COMMENTS[aid][sDay] = sTxt
	return COMMENTS

async def speHours(session, sid, limit = 14, userLang = True):
	sif = storeInfo(sid)
	sid = StoreID(sid)[0][0]
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
		dayIndex = dayOfWeek.index(regular["name"])
		regularHours[dayIndex] = textConvert(regular, userLang = userLang)
	
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
		spetext = textConvert(special, userLang = userLang)

		if validDate < specialToday:# or regular == spetext:
			continue
		if validDate in specialReasons.get(sid, {}):
			reason = {"reason": specialReasons[sid][validDate]}
		else:
			reason = {}
		
		regular = regularHours[validDate.weekday()]
		specialHours[str(validDate)] = {"regular": regular, "special": spetext, **reason}
	specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))
	return specialHours