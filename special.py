import logging, requests, json
from datetime import timedelta, date, datetime
from storeInfo import storeInfo, storeURL, userAgent, storePage
from constants import dayOfWeekENG, partSample, storeNation

def dateConvert(strdate):
	year, month, day = strdate.split("-")
	standard = date(int(year), 1, 1)
	actual = standard + timedelta(days = int(day) - 1)
	return actual

def comment(sid):
	try:
		flag = storeInfo(sid)['flag']
		partNumber = f"MX0K2{partSample[flag]}/A"
	except KeyError:
		return {}
	baseURL = f"https://www.apple.com{storeNation[flag]}"
	referer = {**userAgent, "Referer": f"{baseURL}/shop/product/{partNumber}"}
	url = f"{baseURL}/shop/fulfillment-messages?searchNearby=false&parts.0={partNumber}&store=R{sid}"

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

def speHours(sid, r, mode = "special"):
	url = storeURL(sid)
	if url == "N/A":
		logging.error(f"未能匹配到 R{sid} 的零售店官网页面地址")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0
	logging.info(f"访问 R{sid} 的零售店官网页面")
	
	try:
		j = json.loads(r.split('<script type="application/ld+json">')[1].split("</script>")[0])
	except IndexError:
		logging.error(f"未能从 R{sid} 的零售店官网页面地址匹配到营业时间信息")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0

	regularHours = [""] * 7
	if "openingHoursSpecification" not in j:
		logging.error(f"未能从 R{sid} 的零售店官网页面地址匹配到营业时间信息")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0

	for regular in j["openingHoursSpecification"]:
		for day in regular["dayOfWeek"]:
			if "opens" not in regular:
				regularHours[dayOfWeekENG.index(day)] = "已关闭"
			elif regular["opens"] == "00:00" and regular["closes"] == "23:59":
				regularHours[dayOfWeekENG.index(day)] = "24 小时营业"
			else:
				regularHours[dayOfWeekENG.index(day)] = f'{regular["opens"]} - {regular["closes"]}'
	
	specialHours = {}
	if j["specialOpeningHoursSpecification"]:
		specialReasons = comment(sid)
		for special in j["specialOpeningHoursSpecification"]:
			validDates = []
			startDate = max(date.today(), dateConvert(special["validFrom"]))
			endDate = min(date.today() + timedelta(days = 13), dateConvert(special["validThrough"]))
			while startDate <= endDate:
				validDates.append(startDate)
				startDate += timedelta(days = 1)

			for validDate in validDates:
				if validDate in specialReasons:
					reason = {"reason": specialReasons[validDate]}
				else:
					reason = {}
				fRegular = regularHours[validDate.weekday()]
				if "opens" not in special:
					if fRegular == "已关闭":
						continue
					specialDict = {"regular": fRegular, "special": "已关闭", **reason}
				else:
					fSpecial = f'{special["opens"]} - {special["closes"]}'
					if fRegular == fSpecial:
						continue
					specialDict = {"regular": fRegular, "special": fSpecial, **reason}
				specialHours[str(validDate)] = specialDict
		specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))

	if mode == "special":
		return specialHours
	if mode == "regular":
		return regularHours, len(specialHours)