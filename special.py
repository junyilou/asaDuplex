import logging, requests, json
from datetime import timedelta, date
from storeInfo import storeInfo, storeURL, userAgent

dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def dateConvert(strdate):
	year, month, day = strdate.split("-")
	standard = date(int(year), 1, 1)
	actual = standard + timedelta(days = int(day) - 1)
	return actual

def speHours(sid, mode = "special"):
	url = storeURL(sid)
	if url == "N/A":
		logging.error(f"未能匹配到 R{sid} 的零售店官网页面地址")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0
	logging.info(f"访问 R{sid} 的零售店官网页面")
	r = requests.get(url, headers = userAgent).text
	
	try:
		j = json.loads(r.split('<script type="application/ld+json">')[1].split("</script>")[0])
	except IndexError:
		logging.error(f"未能从 R{sid} 的零售店官网页面地址匹配到营业时间信息")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0

	regularHours = [""] * 7
	for regular in j["openingHoursSpecification"]:
		for day in regular["dayOfWeek"]:
			if "opens" not in regular:
				regularHours[dayOfWeek.index(day)] = "已关闭"
			elif regular["opens"] == "00:00" and regular["closes"] == "23:59":
				regularHours[dayOfWeek.index(day)] = "24 小时营业"
			else:
				regularHours[dayOfWeek.index(day)] = f'{regular["opens"]} - {regular["closes"]}'
	
	specialHours = {}
	for special in j["specialOpeningHoursSpecification"]:
		validDates = []
		startDate = max(date.today(), dateConvert(special["validFrom"]))
		endDate = min(date.today() + timedelta(days = 13), dateConvert(special["validThrough"]))
		while startDate <= endDate:
			validDates.append(startDate)
			startDate += timedelta(days = 1)

		for validDate in validDates:
			fRegular = regularHours[validDate.weekday()]
			if "opens" not in special:
				specialDict = {"regular": fRegular, "special": "已关闭"}
			else:
				fSpecial = f'{special["opens"]} - {special["closes"]}'
				if fRegular == fSpecial:
					break
				specialDict = {"regular": fRegular, "special": fSpecial}
			specialHours[str(validDate)] = specialDict
	specialHours = dict(sorted(specialHours.items(), key = lambda k: k[0]))

	if mode == "special":
		return specialHours
	if mode == "regular":
		return regularHours, len(specialHours)