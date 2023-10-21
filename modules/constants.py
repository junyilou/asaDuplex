from dataclasses import dataclass
from typing import Optional

userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}

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

@dataclass
class Region:
	abbr: str
	job_code: Optional[dict[str, int]]
	locale: str
	name: str
	name_alter: list[str]
	name_eng: str
	part_sample: Optional[str]
	url_app: Optional[str]
	url_taa: str
	url_retail: str
	url_store: Optional[str]

Regions = {
	"BE": Region(
		abbr = "BENL",
		job_code = None,
		locale = "nl_BE",
		name = "比利时 (荷兰语)",
		name_alter = [
			"België"
		],
		name_eng = "Belgium (Dutch)",
		part_sample = "ZM",
		url_app = "e/be-nl",
		url_retail = "/benl",
		url_store = "/be-nl",
		url_taa = "/benl"
	),
	"CA": Region(
		abbr = "CAFR",
		job_code = None,
		locale = "fr_CA",
		name = "加拿大 (法语)",
		name_alter = [],
		name_eng = "Canada (French)",
		part_sample = "AM",
		url_app = "a/xf",
		url_retail = "/ca/fr",
		url_store = "/xf",
		url_taa = "/ca/fr"
	),
	"CH": Region(
		abbr = "CHDE",
		job_code = None,
		locale = "de_CH",
		name = "瑞士 (德语)",
		name_alter = [
			"Schweiz"
		],
		name_eng = "Switzerland (German)",
		part_sample = "ZM",
		url_app = "e/ch-de",
		url_retail = "/chde",
		url_store = "/ch-de",
		url_taa = "/chde"
	),
	"HK": Region(
		abbr = "HKEN",
		job_code = None,
		locale = "en_HK",
		name = "香港 (英语)",
		name_alter = [],
		name_eng = "Hong Kong (English)",
		part_sample = "FE",
		url_app = "p/hk",
		url_retail = "/hk/en",
		url_store = "/hk",
		url_taa = "/hk/en"
	),
	"🇦🇪": Region(
		abbr = "AE",
		job_code = {
			"expert": 114438218,
			"genius": 114438219,
			"specialist": 114438225
		},
		locale = "en_AE",
		name = "阿联酋",
		name_alter = [
			"UAE",
			"阿聯酋",
			"阿拉伯联合酋长国",
			"阿拉伯聯合酋長國"
		],
		name_eng = "United Arab Emirates",
		part_sample = "ZE",
		url_app = "e/ae",
		url_retail = "/ae",
		url_store = "/ae",
		url_taa = "/ae"
	),
	"🇦🇹": Region(
		abbr = "AT",
		job_code = {
			"expert": 114438333,
			"genius": 114438334,
			"specialist": 114438340
		},
		locale = "de_AT",
		name = "奥地利",
		name_alter = [],
		name_eng = "Austria",
		part_sample = "ZM",
		url_app = "e/at",
		url_retail = "/at",
		url_store = "/at",
		url_taa = "/at"
	),
	"🇦🇺": Region(
		abbr = "AU",
		job_code = {
			"expert": 114437983,
			"genius": 114437984,
			"specialist": 114437991
		},
		locale = "en_AU",
		name = "澳大利亚",
		name_alter = [
			"澳洲"
		],
		name_eng = "Australia",
		part_sample = "FE",
		url_app = "p/au",
		url_retail = "/au",
		url_store = "/au",
		url_taa = "/au"
	),
	"🇧🇪": Region(
		abbr = "BE",
		job_code = {
			"expert": 114438244,
			"genius": 114438245,
			"specialist": 114438251
		},
		locale = "fr_BE",
		name = "比利时",
		name_alter = [
			"比利時",
			"Belgique"
		],
		name_eng = "Belgium",
		part_sample = "ZM",
		url_app = "e/be-fr",
		url_retail = "/befr",
		url_store = "/be-fr",
		url_taa = "/befr"
	),
	"🇧🇷": Region(
		abbr = "BR",
		job_code = {
			"expert": 114438177,
			"genius": 114438178,
			"specialist": 114438176
		},
		locale = "pt_BR",
		name = "巴西",
		name_alter = [],
		name_eng = "Brazil",
		part_sample = "AM",
		url_app = "a/br",
		url_retail = "/br",
		url_store = "/br",
		url_taa = "/br"
	),
	"🇨🇦": Region(
		abbr = "CA",
		job_code = {
			"expert": 114437996,
			"genius": 114437997,
			"specialist": 114438004
		},
		locale = "en_CA",
		name = "加拿大",
		name_alter = [],
		name_eng = "Canada",
		part_sample = "AM",
		url_app = "a/ca",
		url_retail = "/ca",
		url_store = "/ca",
		url_taa = "/ca"
	),
	"🇨🇭": Region(
		abbr = "CH",
		job_code = {
			"expert": 114438009,
			"genius": 114438010,
			"specialist": 114438017
		},
		locale = "fr_CH",
		name = "瑞士",
		name_alter = [
			"Swiss",
			"Suisse"
		],
		name_eng = "Switzerland",
		part_sample = "ZM",
		url_app = "e/ch-fr",
		url_retail = "/chfr",
		url_store = "/ch-fr",
		url_taa = "/chfr"
	),
	"🇨🇳": Region(
		abbr = "CN",
		job_code = {
			"expert": 114438022,
			"genius": 114438023,
			"specialist": 114438030
		},
		locale = "zh_CN",
		name = "中国",
		name_alter = [
			"中國",
			"中华人民共和国",
			"中華人民共和國",
			"China mainland",
			"PRC"
		],
		name_eng = "China",
		part_sample = "FE",
		url_app = "p/cn",
		url_retail = ".cn",
		url_store = ".cn",
		url_taa = "/cn"
	),
	"🇩🇪": Region(
		abbr = "DE",
		job_code = {
			"expert": 114438035,
			"genius": 114438036,
			"specialist": 114438043
		},
		locale = "de_DE",
		name = "德国",
		name_alter = [
			"德國",
			"Deutschland"
		],
		name_eng = "Germany",
		part_sample = "ZM",
		url_app = "e/de",
		url_retail = "/de",
		url_store = "/de",
		url_taa = "/de"
	),
	"🇪🇸": Region(
		abbr = "ES",
		job_code = {
			"expert": 114438048,
			"genius": 114438049,
			"specialist": 114438056
		},
		locale = "es_ES",
		name = "西班牙",
		name_alter = [
			"España"
		],
		name_eng = "Spain",
		part_sample = "ZM",
		url_app = "e/es",
		url_retail = "/es",
		url_store = "/es",
		url_taa = "/es"
	),
	"🇫🇷": Region(
		abbr = "FR",
		job_code = {
			"expert": 114438061,
			"genius": 114438062,
			"specialist": 114438069
		},
		locale = "fr_FR",
		name = "法国",
		name_alter = [
			"法國",
			"法兰西共和国",
			"法蘭西共和國"
		],
		name_eng = "France",
		part_sample = "ZM",
		url_app = "e/fr",
		url_retail = "/fr",
		url_store = "/fr",
		url_taa = "/fr"
	),
	"🇬🇧": Region(
		abbr = "GB",
		job_code = {
			"expert": 114438137,
			"genius": 114438138,
			"specialist": 114438145
		},
		locale = "en_GB",
		name = "英国",
		name_alter = [
			"UK",
			"U.K.",
			"Great Britain",
			"大英帝国",
			"大英帝國"
		],
		name_eng = "United Kingdom",
		part_sample = "ZM",
		url_app = "e/uk",
		url_retail = "/uk",
		url_store = "/uk",
		url_taa = "/uk"
	),
	"🇭🇰": Region(
		abbr = "HK",
		job_code = {
			"expert": 114438074,
			"genius": 114438075,
			"specialist": 114438082
		},
		locale = "zh_HK",
		name = "香港",
		name_alter = [
			"香港特别行政区",
			"香港特別行政區"
		],
		name_eng = "Hong Kong",
		part_sample = "FE",
		url_app = "p/hk-zh",
		url_retail = "/hk",
		url_store = "/hk-zh",
		url_taa = "/hk"
	),
	"🇮🇳": Region(
		abbr = "IN",
		job_code = {
			"expert": 200314010,
			"genius": 200314015,
			"technical": 200314122
		},
		locale = "en_IN",
		name = "印度",
		name_alter = [],
		name_eng = "India",
		part_sample = "ZM",
		url_app = None,
		url_retail = "/in",
		url_store = "/in",
		url_taa = "/in"
	),
	"🇮🇹": Region(
		abbr = "IT",
		job_code = {
			"expert": 114438087,
			"genius": 114438088,
			"specialist": 114438095
		},
		locale = "it_IT",
		name = "意大利",
		name_alter = [
			"Italia",
			"义大利"
		],
		name_eng = "Italy",
		part_sample = "ZM",
		url_app = "e/it",
		url_retail = "/it",
		url_store = "/it",
		url_taa = "/it"
	),
	"🇯🇵": Region(
		abbr = "JP",
		job_code = {
			"specialist": 114438107
		},
		locale = "ja_JP",
		name = "日本",
		name_alter = [],
		name_eng = "Japan",
		part_sample = "FE",
		url_app = "j/jp",
		url_retail = "/jp",
		url_store = "/jp",
		url_taa = "/jp"
	),
	"🇰🇷": Region(
		abbr = "KR",
		job_code = {
			"expert": 114438319,
			"genius": 114438320,
			"specialist": 114438326
		},
		locale = "ko_KR",
		name = "韩国",
		name_alter = [
			"Korea",
			"ROK",
			"南韩",
			"南韓",
			"大韩民国",
			"大韓民國"
		],
		name_eng = "South Korea",
		part_sample = "FE",
		url_app = "p/kr",
		url_retail = "/kr",
		url_store = "/kr",
		url_taa = "/kr"
	),
	"🇲🇴": Region(
		abbr = "MO",
		job_code = {
			"expert": 114438275,
			"genius": 114438276,
			"specialist": 114438282
		},
		locale = "zh_MO",
		name = "澳门",
		name_alter = [
			"澳門",
			"澳门特别行政区",
			"澳門特別行政區",
			"Macao"
		],
		name_eng = "Macau",
		part_sample = None,
		url_app = None,
		url_retail = "/mo",
		url_store = None,
		url_taa = "/mo"
	),
	"🇲🇽": Region(
		abbr = "MX",
		job_code = {
			"expert": 114438290,
			"genius": 114438291,
			"specialist": 114438297
		},
		locale = "es_MX",
		name = "墨西哥",
		name_alter = [],
		name_eng = "Mexico",
		part_sample = "AM",
		url_app = "a/mx",
		url_retail = "/mx",
		url_store = "/mx",
		url_taa = "/mx"
	),
	"🇲🇾": Region(
		abbr = "MY",
		job_code = {
			"expert": 200450004,
			"genius": 200450000,
			"specialist": 200450003
		},
		locale = "en_MY",
		name = "马来西亚",
		name_alter = [
			"馬來西亞",
			"大马"
		],
		name_eng = "Malaysia",
		part_sample = "FE",
		url_app = "p/my",
		url_retail = "/my",
		url_store = "/my",
		url_taa = "/my"
	),
	"🇳🇱": Region(
		abbr = "NL",
		job_code = {
			"expert": 114438111,
			"genius": 114438112,
			"specialist": 114438119
		},
		locale = "nl_NL",
		name = "荷兰",
		name_alter = [
			"荷蘭",
			"Holland"
		],
		name_eng = "Netherlands",
		part_sample = "ZM",
		url_app = "e/nl",
		url_retail = "/nl",
		url_store = "/nl",
		url_taa = "/nl"
	),
	"🇸🇪": Region(
		abbr = "SE",
		job_code = {
			"expert": 114438124,
			"genius": 114438125,
			"specialist": 114438132
		},
		locale = "sv_SE",
		name = "瑞典",
		name_alter = [],
		name_eng = "Sweden",
		part_sample = "ZM",
		url_app = "e/se",
		url_retail = "/se",
		url_store = "/se",
		url_taa = "/se"
	),
	"🇸🇬": Region(
		abbr = "SG",
		job_code = {
			"specialist": 114438238
		},
		locale = "en_SG",
		name = "新加坡",
		name_alter = [
			"星加坡"
		],
		name_eng = "Singapore",
		part_sample = "FE",
		url_app = "p/sg",
		url_retail = "/sg",
		url_store = "/sg",
		url_taa = "/sg"
	),
	"🇹🇭": Region(
		abbr = "TH",
		job_code = {
			"specialist": 114438346
		},
		locale = "th_TH",
		name = "泰国",
		name_alter = [
			"泰國"
		],
		name_eng = "Thailand",
		part_sample = "FE",
		url_app = "p/th-en",
		url_retail = "/th",
		url_store = "/th",
		url_taa = "/th"
	),
	"🇹🇷": Region(
		abbr = "TR",
		job_code = {
			"expert": 114438165,
			"genius": 114438166,
			"specialist": 114438164
		},
		locale = "tr_TR",
		name = "土耳其",
		name_alter = [],
		name_eng = "Turkey",
		part_sample = "ZM",
		url_app = "e/tr",
		url_retail = "/tr",
		url_store = "/tr",
		url_taa = "/tr"
	),
	"🇹🇼": Region(
		abbr = "TW",
		job_code = {
			"expert": 114438305,
			"genius": 114438306,
			"specialist": 114438311
		},
		locale = "zh_TW",
		name = "台湾",
		name_alter = [
			"ROC",
			"中华民国",
			"中華民國"
		],
		name_eng = "Taiwan",
		part_sample = "FE",
		url_app = "p/tw",
		url_retail = "/tw",
		url_store = "/tw",
		url_taa = "/tw"
	),
	"🇺🇸": Region(
		abbr = "US",
		job_code = {
			"expert": 114438150,
			"genius": 114438151,
			"specialist": 114438158
		},
		locale = "en_US",
		name = "美国",
		name_alter = [
			"美國",
			"America",
			"U.S."
		],
		name_eng = "United States",
		part_sample = "AM",
		url_app = "a/us",
		url_retail = "",
		url_store = "",
		url_taa = ""
	)
}