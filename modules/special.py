import logging
import requests
import json
from datetime import timedelta, date, datetime
from storeInfo import storeInfo, storeDict
from modules.constants import userAgent, dayOfWeekENG, partSample, storeNation, textConvert

'''
def dateConvert(strdate):
	year, month, day = strdate.split("-")
	standard = date(int(year), 1, 1)
	actual = standard + timedelta(days = int(day) - 1)
	return actual
'''

def comment(sid):
	try:
		flag = storeInfo(sid)['flag']
		partNumber = f"MM0A3{partSample[flag]}/A"
	except KeyError:
		return {}
	baseURL = f"https://www.apple.com{storeNation[flag]}"
	referer = {**userAgent, "Referer": f"{baseURL}/shop/product/{partNumber}"}
	url = f"{baseURL}/shop/fulfillment-messages?searchNearby=true&parts.0={partNumber}&store=R{sid}"

	try:
		r = requests.get(url, headers = referer).json()
		j = r["body"]["content"]["pickupMessage"]["stores"]
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

def speHours(sid):
	try:
		j = storeDict(sid, mode = "hours")
	except:
		logging.error(f"未能获得 R{sid} 营业时间信息")
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
		specialReasons = comment(sid)
	for special in j["special"]:
		if len(specialHours) == 14:
			break

		validDate = datetime.strptime(special["date"], "%Y-%m-%d").date()
		regular = regularHours[validDate.weekday()]
		spetext = textConvert(special)

		if validDate < specialToday or regular == spetext:
			continue
		if validDate in specialReasons:
			reason = {"reason": specialReasons[validDate]}
		else:
			reason = {}
		
		regular = regularHours[validDate.weekday()]
		specialHours[str(validDate)] = {"regular": regular, "special": spetext, **reason}
	specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))
	return specialHours