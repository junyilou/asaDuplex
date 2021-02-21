import logging, requests, json
from datetime import datetime, timedelta
from storeInfo import storeInfo

userAgent = {
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15\
	 (KHTML, like Gecko) Version/14.0.2 Safari/605.1.15"
}

nationCode = {
	"🇺🇸": "", "🇨🇳": "cn", "🇬🇧": "uk", "🇨🇦": "ca", "🇦🇺": "au", "🇫🇷": "fr", "🇮🇹": "it",
	"🇩🇪": "de", "🇪🇸": "es", "🇯🇵": "jp", "🇨🇭": "chde", "🇦🇪": "ae", "🇳🇱": "nl", "🇸🇪": "se",
	"🇧🇷": "br", "🇹🇷": "tr", "🇸🇬": "sg", "🇲🇽": "mx", "🇦🇹": "at", "🇧🇪": "befr", "🇰🇷": "kr",
	"🇹🇭": "th", "🇭🇰": "hk", "🇲🇴": "mo", "🇹🇼": "tw", "TW": "tw"
}
nationCode = dict([(i[0], f"/{i[1]}") if i[0] != "🇺🇸" else i for i in nationCode.items()])

dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def speHours(sid, mode = "special"):
	try:
		sif = storeInfo(sid)
		url = f"https://www.apple.com{nationCode[sif['flag']]}/retail/{sif['website']}"
	except KeyError:
		logging.error(f"未能匹配到 R{sid} 的零售店官网页面地址")
		if mode == "special":
			return {}
		if mode == "regular":
			return {}, 0
	logging.info(f"访问 R{sid} 的零售店官网页面")
	r = requests.get(url, headers = userAgent).text
	j = json.loads(r.split('<script type="application/ld+json">')[1].split("</script>")[0])

	regularHours = [""] * 7
	for regular in j["openingHoursSpecification"]:
		for day in regular["dayOfWeek"]:
			if regular["opens"] == regular["closes"] == "24:00:00":
				regularHours[dayOfWeek.index(day)] = "已关闭"
			elif regular["opens"] == "24:00:00" and regular["closes"] == "23:59:00":
				regularHours[dayOfWeek.index(day)] = "24 小时营业"
			else:
				regularHours[dayOfWeek.index(day)] = f"{regular['opens'][:-3]} - {regular['closes'][:-3]}"
	
	specialHours = {}
	for special in j["specialOpeningHoursSpecification"]:
		validDates = []
		startDate = max(datetime.now().date(), datetime.strptime(special["validFrom"], "%Y-%m-%d").date())
		endDate = datetime.strptime(special["validThrough"], "%Y-%m-%d").date()
		while startDate <= endDate:
			validDates.append(startDate)
			startDate += timedelta(days = 1)
		for validDate in validDates:
			fRegular = regularHours[validDate.weekday()]
			if "opens" in special.keys():
				specialDict = {"regular": fRegular, "special": f"{special['opens'][:-3]} - {special['closes'][:-3]}"}
			else:
				specialDict = {"regular": fRegular, "special": "已关闭"}
			specialHours[datetime.strftime(validDate, "%Y-%m-%d")] = specialDict

	if mode == "special":
		return specialHours
	if mode == "regular":
		return regularHours, len(specialHours)