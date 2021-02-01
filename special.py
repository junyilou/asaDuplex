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
	"🇹🇭": "th", "🇭🇰": "hk", "🇲🇴": "mo", "🇹🇼": "tw"
}

dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def speHours(sid):
	try:
		sif = storeInfo(sid)
		url = "https://www.apple.com/{}/retail/{}".format(nationCode[sif["flag"]], sif["website"])
	except KeyError:
		logging.error("未能匹配到 R{} 的零售店官网页面地址".format(sid))
		return {}
	logging.info("正在访问 R{} 的零售店官网页面".format(sid))
	r = requests.get(url, headers = userAgent).text
	j = json.loads(r.split('<script type="application/ld+json">')[1].split("</script>")[0])

	regularHours = [""] * 7
	for regular in j["openingHoursSpecification"]:
		for day in regular["dayOfWeek"]:
			if regular["opens"] == regular["closes"] == "24:00:00":
				regularHours[dayOfWeek.index(day)] = "已关闭"
			if regular["opens"] == "24:00:00" and regular["closes"] == "23:59:00":
				regularHours[dayOfWeek.index(day)] = "24 小时营业"
			else:
				regularHours[dayOfWeek.index(day)] = "{} - {}".format(regular["opens"][:-3], regular["closes"][:-3])
	
	specialHours = {}
	for special in j["specialOpeningHoursSpecification"]:
		validDates = []
		startDate = datetime.strptime(special["validFrom"], "%Y-%m-%d").date()
		endDate = datetime.strptime(special["validThrough"], "%Y-%m-%d").date()
		while startDate <= endDate:
			validDates.append(startDate)
			startDate += timedelta(days = 1)
		for validDate in validDates:
			fRegular = regularHours[validDate.weekday()]
			if "opens" in special.keys():
				specialDict = {"regular": fRegular, "special": "{} - {}".format(special["opens"][:-3], special["closes"][:-3])}
			else:
				specialDict = {"regular": fRegular, "special": "已关闭"}
			specialHours[datetime.strftime(validDate, "%Y年%-m月%-d日")] = specialDict

	return specialHours