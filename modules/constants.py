from typing import Any, NotRequired, Optional, TypedDict

userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"}

partRuleCheck = r"([FGHMNPS][0-9A-Z]{3}[0-9]([A-Z]{1,2}/[A-Z])?)"

DIFFHTML = """<!DOCTYPE html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{DIFFTITLE}</title>
</head>
<body><pre><code>
{DIFFCONTENT}
</code></pre></body>
</html>"""

class RegionDict(TypedDict):
	abbr: str
	altername: list[str]
	eppURL: NotRequired[dict[str, Optional[str]]]
	jobCode: Optional[dict[str, int]]
	mobileApp: Optional[str]
	name: str
	nameEng: str
	partSample: Optional[str]
	rootPath: str
	rspLocale: str
	shopURL: Optional[str]
	storeURL: str

allRegions: dict[str, RegionDict] = {
	"BE": {
		"abbr": "BENL",
		"altername": [
			"比利時"
		],
		"jobCode": None,
		"mobileApp": "e/be-nl",
		"name": "比利时 (荷兰语)",
		"nameEng": "Belgium (Dutch)",
		"partSample": "ZM",
		"rootPath": "/benl",
		"rspLocale": "nl_BE",
		"shopURL": "/be-nl",
		"storeURL": "/benl"
	},
	"CA": {
		"abbr": "CAFR",
		"altername": [],
		"jobCode": None,
		"mobileApp": "a/xf",
		"name": "加拿大 (法语)",
		"nameEng": "Canada (French)",
		"partSample": "AM",
		"rootPath": "/ca/fr",
		"rspLocale": "fr_CA",
		"shopURL": "/xf",
		"storeURL": "/ca/fr"
	},
	"CH": {
		"abbr": "CHDE",
		"altername": [
			"Swiss"
		],
		"jobCode": None,
		"mobileApp": "e/ch-de",
		"name": "瑞士 (德语)",
		"nameEng": "Switzerland (German)",
		"partSample": "ZM",
		"rootPath": "/chde",
		"rspLocale": "de_CH",
		"shopURL": "/ch-de",
		"storeURL": "/chde"
	},
	"HK": {
		"abbr": "HKEN",
		"altername": [],
		"jobCode": None,
		"mobileApp": "p/hk",
		"name": "香港 (英语)",
		"nameEng": "Hong Kong (English)",
		"partSample": "FE",
		"rootPath": "/hk/en",
		"rspLocale": "en_HK",
		"shopURL": "/hk",
		"storeURL": "/hk/en"
	},
	"🇦🇪": {
		"abbr": "AE",
		"altername": [
			"UAE",
			"阿聯酋",
			"阿拉伯联合酋长国",
			"阿拉伯聯合酋長國"
			"阿拉伯联合大公国"
		],
		"jobCode": {
			"expert": 114438218,
			"genius": 114438219,
			"specialist": 114438225
		},
		"mobileApp": "e/ae",
		"name": "阿联酋",
		"nameEng": "United Arab Emirates",
		"partSample": "ZE",
		"rootPath": "/ae",
		"rspLocale": "en_AE",
		"shopURL": "/ae",
		"storeURL": "/ae"
	},
	"🇦🇹": {
		"abbr": "AT",
		"altername": [],
		"jobCode": {
			"expert": 114438333,
			"genius": 114438334,
			"specialist": 114438340
		},
		"mobileApp": "e/at",
		"name": "奥地利",
		"nameEng": "Austria",
		"partSample": "ZM",
		"rootPath": "/at",
		"rspLocale": "de_AT",
		"shopURL": "/at",
		"storeURL": "/at"
	},
	"🇦🇺": {
		"abbr": "AU",
		"altername": [
			"澳洲"
		],
		"jobCode": {
			"expert": 114437983,
			"genius": 114437984,
			"specialist": 114437991
		},
		"mobileApp": "p/au",
		"name": "澳大利亚",
		"nameEng": "Australia",
		"partSample": "FE",
		"rootPath": "/au",
		"rspLocale": "en_AU",
		"shopURL": "/au",
		"storeURL": "/au"
	},
	"🇧🇪": {
		"abbr": "BE",
		"altername": [
			"比利時"
		],
		"jobCode": {
			"expert": 114438244,
			"genius": 114438245,
			"specialist": 114438251
		},
		"mobileApp": "e/be-fr",
		"name": "比利时",
		"nameEng": "Belgium",
		"partSample": "ZM",
		"rootPath": "/befr",
		"rspLocale": "fr_BE",
		"shopURL": "/be-fr",
		"storeURL": "/befr"
	},
	"🇧🇷": {
		"abbr": "BR",
		"altername": [],
		"jobCode": {
			"expert": 114438177,
			"genius": 114438178,
			"specialist": 114438176
		},
		"mobileApp": "a/br",
		"name": "巴西",
		"nameEng": "Brazil",
		"partSample": "AM",
		"rootPath": "/br",
		"rspLocale": "pt_BR",
		"shopURL": "/br",
		"storeURL": "/br"
	},
	"🇨🇦": {
		"abbr": "CA",
		"altername": [],
		"jobCode": {
			"expert": 114437996,
			"genius": 114437997,
			"specialist": 114438004
		},
		"mobileApp": "a/ca",
		"name": "加拿大",
		"nameEng": "Canada",
		"partSample": "AM",
		"rootPath": "/ca",
		"rspLocale": "en_CA",
		"shopURL": "/ca",
		"storeURL": "/ca"
	},
	"🇨🇭": {
		"abbr": "CH",
		"altername": [
			"Swiss"
		],
		"jobCode": {
			"expert": 114438009,
			"genius": 114438010,
			"specialist": 114438017
		},
		"mobileApp": "e/ch-fr",
		"name": "瑞士",
		"nameEng": "Switzerland",
		"partSample": "ZM",
		"rootPath": "/chfr",
		"rspLocale": "fr_CH",
		"shopURL": "/ch-fr",
		"storeURL": "/chfr"
	},
	"🇨🇳": {
		"abbr": "CN",
		"altername": [
			"中國",
			"中华人民共和国",
			"中華人民共和國",
			"China mainland",
			"PRC"
		],
		"jobCode": {
			"expert": 114438022,
			"genius": 114438023,
			"specialist": 114438030
		},
		"mobileApp": "p/cn",
		"name": "中国",
		"nameEng": "China",
		"partSample": "FE",
		"rootPath": "/cn",
		"rspLocale": "zh_CN",
		"shopURL": ".cn",
		"storeURL": ".cn"
	},
	"🇩🇪": {
		"abbr": "DE",
		"altername": [
			"德國",
			"Deutschland"
		],
		"jobCode": {
			"expert": 114438035,
			"genius": 114438036,
			"specialist": 114438043
		},
		"mobileApp": "e/de",
		"name": "德国",
		"nameEng": "Germany",
		"partSample": "ZM",
		"rootPath": "/de",
		"rspLocale": "de_DE",
		"shopURL": "/de",
		"storeURL": "/de"
	},
	"🇪🇸": {
		"abbr": "ES",
		"altername": [
			"España"
		],
		"jobCode": {
			"expert": 114438048,
			"genius": 114438049,
			"specialist": 114438056
		},
		"mobileApp": "e/es",
		"name": "西班牙",
		"nameEng": "Spain",
		"partSample": "ZM",
		"rootPath": "/es",
		"rspLocale": "es_ES",
		"shopURL": "/es",
		"storeURL": "/es"
	},
	"🇫🇷": {
		"abbr": "FR",
		"altername": [
			"法國",
			"法兰西共和国",
			"法蘭西共和國"
		],
		"jobCode": {
			"expert": 114438061,
			"genius": 114438062,
			"specialist": 114438069
		},
		"mobileApp": "e/fr",
		"name": "法国",
		"nameEng": "France",
		"partSample": "ZM",
		"rootPath": "/fr",
		"rspLocale": "fr_FR",
		"shopURL": "/fr",
		"storeURL": "/fr"
	},
	"🇬🇧": {
		"abbr": "GB",
		"altername": [
			"UK",
			"Great Britain",
			"大英帝国",
			"大英帝國"
		],
		"jobCode": {
			"expert": 114438137,
			"genius": 114438138,
			"specialist": 114438145
		},
		"mobileApp": "e/uk",
		"name": "英国",
		"nameEng": "United Kingdom",
		"partSample": "ZM",
		"rootPath": "/uk",
		"rspLocale": "en_GB",
		"shopURL": "/uk",
		"storeURL": "/uk"
	},
	"🇭🇰": {
		"abbr": "HK",
		"altername": [
			"香港特别行政区",
			"香港特別行政區"
		],
		"jobCode": {
			"expert": 114438074,
			"genius": 114438075,
			"specialist": 114438082
		},
		"mobileApp": "p/hk-zh",
		"name": "香港",
		"nameEng": "Hong Kong",
		"partSample": "FE",
		"rootPath": "/hk",
		"rspLocale": "zh_HK",
		"shopURL": "/hk-zh",
		"storeURL": "/hk"
	},
	"🇮🇳": {
		"abbr": "IN",
		"altername": [],
		"jobCode": {
			"expert": 200314010,
			"genius": 200314015,
			"technical": 200314122
		},
		"mobileApp": None,
		"name": "印度",
		"nameEng": "India",
		"partSample": "ZM",
		"rootPath": "/in",
		"rspLocale": "en_IN",
		"shopURL": "/in",
		"storeURL": "/in"
	},
	"🇮🇹": {
		"abbr": "IT",
		"altername": [
			"Italia",
			"义大利"
		],
		"jobCode": {
			"expert": 114438087,
			"genius": 114438088,
			"specialist": 114438095
		},
		"mobileApp": "e/it",
		"name": "意大利",
		"nameEng": "Italy",
		"partSample": "ZM",
		"rootPath": "/it",
		"rspLocale": "it_IT",
		"shopURL": "/it",
		"storeURL": "/it"
	},
	"🇯🇵": {
		"abbr": "JP",
		"altername": [],
		"jobCode": {
			"specialist": 114438107
		},
		"mobileApp": "j/jp",
		"name": "日本",
		"nameEng": "Japan",
		"partSample": "FE",
		"rootPath": "/jp",
		"rspLocale": "ja_JP",
		"shopURL": "/jp",
		"storeURL": "/jp"
	},
	"🇰🇷": {
		"abbr": "KR",
		"altername": [
			"Korea",
			"ROK",
			"南韩",
			"南韓",
			"大韩民国",
			"大韓民國"
		],
		"jobCode": {
			"expert": 114438319,
			"genius": 114438320,
			"specialist": 114438326
		},
		"mobileApp": "p/kr",
		"name": "韩国",
		"nameEng": "South Korea",
		"partSample": "FE",
		"rootPath": "/kr",
		"rspLocale": "ko_KR",
		"shopURL": "/kr",
		"storeURL": "/kr"
	},
	"🇲🇴": {
		"abbr": "MO",
		"altername": [
			"澳門",
			"澳门特别行政区",
			"澳門特別行政區",
			"Macao"
		],
		"jobCode": {
			"expert": 114438275,
			"genius": 114438276,
			"specialist": 114438282
		},
		"mobileApp": None,
		"name": "澳门",
		"nameEng": "Macau",
		"partSample": None,
		"rootPath": "/mo",
		"rspLocale": "zh_MO",
		"shopURL": None,
		"storeURL": "/mo"
	},
	"🇲🇽": {
		"abbr": "MX",
		"altername": [],
		"jobCode": {
			"expert": 114438290,
			"genius": 114438291,
			"specialist": 114438297
		},
		"mobileApp": "a/mx",
		"name": "墨西哥",
		"nameEng": "Mexico",
		"partSample": "AM",
		"rootPath": "/mx",
		"rspLocale": "es_MX",
		"shopURL": "/mx",
		"storeURL": "/mx"
	},
	"🇲🇾": {
		"abbr": "MY",
		"altername": [
			"馬來西亞",
			"大马"
		],
		"jobCode": {
			"expert": 200450004,
			"genius": 200450000,
			"specialist": 200450003
		},
		"mobileApp": "p/my",
		"name": "马来西亚",
		"nameEng": "Malaysia",
		"partSample": "FE",
		"rootPath": "/my",
		"rspLocale": "en_MY",
		"shopURL": "/my",
		"storeURL": "/my"
	},
	"🇳🇱": {
		"abbr": "NL",
		"altername": [
			"荷蘭",
			"Holland"
		],
		"jobCode": {
			"expert": 114438111,
			"genius": 114438112,
			"specialist": 114438119
		},
		"mobileApp": "e/nl",
		"name": "荷兰",
		"nameEng": "Netherlands",
		"partSample": "ZM",
		"rootPath": "/nl",
		"rspLocale": "nl_NL",
		"shopURL": "/nl",
		"storeURL": "/nl"
	},
	"🇸🇪": {
		"abbr": "SE",
		"altername": [],
		"jobCode": {
			"expert": 114438124,
			"genius": 114438125,
			"specialist": 114438132
		},
		"mobileApp": "e/se",
		"name": "瑞典",
		"nameEng": "Sweden",
		"partSample": "ZM",
		"rootPath": "/se",
		"rspLocale": "sv_SE",
		"shopURL": "/se",
		"storeURL": "/se"
	},
	"🇸🇬": {
		"abbr": "SG",
		"altername": [
			"星加坡"
		],
		"jobCode": {
			"specialist": 114438238
		},
		"mobileApp": "p/sg",
		"name": "新加坡",
		"nameEng": "Singapore",
		"partSample": "FE",
		"rootPath": "/sg",
		"rspLocale": "en_SG",
		"shopURL": "/sg",
		"storeURL": "/sg"
	},
	"🇹🇭": {
		"abbr": "TH",
		"altername": [
			"泰國"
		],
		"jobCode": {
			"specialist": 114438346
		},
		"mobileApp": "p/th-en",
		"name": "泰国",
		"nameEng": "Thailand",
		"partSample": "FE",
		"rootPath": "/th",
		"rspLocale": "th_TH",
		"shopURL": "/th",
		"storeURL": "/th"
	},
	"🇹🇷": {
		"abbr": "TR",
		"altername": [],
		"jobCode": {
			"expert": 114438165,
			"genius": 114438166,
			"specialist": 114438164
		},
		"mobileApp": "e/tr",
		"name": "土耳其",
		"nameEng": "Turkey",
		"partSample": "ZM",
		"rootPath": "/tr",
		"rspLocale": "tr_TR",
		"shopURL": "/tr",
		"storeURL": "/tr"
	},
	"🇹🇼": {
		"abbr": "TW",
		"altername": [
			"ROC",
			"中华民国",
			"中華民國"
		],
		"jobCode": {
			"expert": 114438305,
			"genius": 114438306,
			"specialist": 114438311
		},
		"mobileApp": "p/tw",
		"name": "台湾",
		"nameEng": "Taiwan",
		"partSample": "FE",
		"rootPath": "/tw",
		"rspLocale": "zh_TW",
		"shopURL": "/tw",
		"storeURL": "/tw"
	},
	"🇺🇸": {
		"abbr": "US",
		"altername": [
			"美國",
			"America",
			"U.S."
		],
		"jobCode": {
			"expert": 114438150,
			"genius": 114438151,
			"specialist": 114438158
		},
		"mobileApp": "a/us",
		"name": "美国",
		"nameEng": "United States",
		"partSample": "AM",
		"rootPath": "",
		"rspLocale": "en_US",
		"shopURL": "",
		"storeURL": ""
	}
}