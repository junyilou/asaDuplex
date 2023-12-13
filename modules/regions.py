from dataclasses import dataclass
from typing import Optional

@dataclass(order = True, frozen = True)
class Region:
	flag: str
	abbr: str
	job_code: dict[str, int]
	locale: str
	name: str
	name_alter: list[str]
	name_eng: str
	part_sample: Optional[str]
	post_location: str
	url_app: Optional[str]
	url_taa: str
	url_retail: str
	url_store: Optional[str]

	def __repr__(self) -> str:
		return f"<Region {self.abbr}: {self.name}>"

RegionList = [
	Region(
		flag = "BE",
		abbr = "BENL",
		job_code = {},
		locale = "nl_BE",
		name = "比利时 (荷兰语)",
		name_alter = [
			"België"
		],
		name_eng = "Belgium (Dutch)",
		part_sample = "ZM",
		post_location = "BELC",
		url_app = "e/be-nl",
		url_retail = "/benl",
		url_store = "/be-nl",
		url_taa = "/benl"
	),
	Region(
		flag = "CA",
		abbr = "CAFR",
		job_code = {},
		locale = "fr_CA",
		name = "加拿大 (法语)",
		name_alter = [],
		name_eng = "Canada (French)",
		part_sample = "AM",
		post_location = "CANC",
		url_app = "a/xf",
		url_retail = "/ca/fr",
		url_store = "/xf",
		url_taa = "/ca/fr"
	),
	Region(
		flag = "CH",
		abbr = "CHDE",
		job_code = {},
		locale = "de_CH",
		name = "瑞士 (德语)",
		name_alter = [
			"Schweiz"
		],
		name_eng = "Switzerland (German)",
		part_sample = "ZM",
		post_location = "CHEC",
		url_app = "e/ch-de",
		url_retail = "/chde",
		url_store = "/ch-de",
		url_taa = "/chde"
	),
	Region(
		flag = "HK",
		abbr = "HKEN",
		job_code = {},
		locale = "en_HK",
		name = "香港 (英语)",
		name_alter = [],
		name_eng = "Hong Kong (English)",
		part_sample = "FE",
		post_location = "HKGC",
		url_app = "p/hk",
		url_retail = "/hk/en",
		url_store = "/hk",
		url_taa = "/hk/en"
	),
	Region(
		flag = "🇦🇪",
		abbr = "AE",
		job_code = {
			"ae-business-pro": 200125467,
			"uae-business-expert": 114438216,
			"uae-creative": 114438217,
			"uae-expert": 114438218,
			"uae-genius": 114438219,
			"uae-operations-expert": 114438220,
			"uae-specialist": 114438225,
			"uae-technical-specialist": 114438224
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
		post_location = "ARE",
		url_app = "e/ae",
		url_retail = "/ae",
		url_store = "/ae",
		url_taa = "/ae"
	),
	Region(
		flag = "🇦🇹",
		abbr = "AT",
		job_code = {
			"at-business-expert-m-f-d": 114438331,
			"at-business-pro-m-f-d": 200125465,
			"at-creative-m-f-d": 114438332,
			"at-expert-m-f-d": 114438333,
			"at-genius-m-f-d": 114438334,
			"at-operations-expert-m-f-d": 114438335,
			"at-specialist-m-f-d": 114438340,
			"at-technical-specialist-m-f-d": 114438339
		},
		locale = "de_AT",
		name = "奥地利",
		name_alter = [],
		name_eng = "Austria",
		part_sample = "ZM",
		post_location = "AUT",
		url_app = "e/at",
		url_retail = "/at",
		url_store = "/at",
		url_taa = "/at"
	),
	Region(
		flag = "🇦🇺",
		abbr = "AU",
		job_code = {
			"au-manager": 114437988,
			"au-senior-manager": 114438252,
			"au-specialist": 114437991
		},
		locale = "en_AU",
		name = "澳大利亚",
		name_alter = [
			"澳洲"
		],
		name_eng = "Australia",
		part_sample = "FE",
		post_location = "AUSC",
		url_app = "p/au",
		url_retail = "/au",
		url_store = "/au",
		url_taa = "/au"
	),
	Region(
		flag = "🇧🇪",
		abbr = "BE",
		job_code = {
			"be-business-expert": 114438242,
			"be-business-pro": 200125384,
			"be-creative": 114438243,
			"be-expert": 114438244,
			"be-genius": 114438245,
			"be-specialist": 114438251,
			"be-technical-specialist": 114438250
		},
		locale = "fr_BE",
		name = "比利时",
		name_alter = [
			"比利時",
			"Belgique"
		],
		name_eng = "Belgium",
		part_sample = "ZM",
		post_location = "BELC",
		url_app = "e/be-fr",
		url_retail = "/befr",
		url_store = "/be-fr",
		url_taa = "/befr"
	),
	Region(
		flag = "🇧🇷",
		abbr = "BR",
		job_code = {
			"br-business-expert": 114438175,
			"br-business-pro": 200125322,
			"br-creative": 114438179,
			"br-expert": 114438177,
			"br-genius": 114438178,
			"br-operations-expert": 114438180,
			"br-specialist": 114438176
		},
		locale = "pt_BR",
		name = "巴西",
		name_alter = [],
		name_eng = "Brazil",
		part_sample = "AM",
		post_location = "BRAC",
		url_app = "a/br",
		url_retail = "/br",
		url_store = "/br",
		url_taa = "/br"
	),
	Region(
		flag = "🇨🇦",
		abbr = "CA",
		job_code = {
			"ca-business-expert": 114437994,
			"ca-business-pro": 200125332,
			"ca-creative": 114437995,
			"ca-expert": 114437996,
			"ca-genius": 114437997,
			"ca-operations-expert": 114437998,
			"ca-specialist": 114438004,
			"ca-technical-specialist": 114438200
		},
		locale = "en_CA",
		name = "加拿大",
		name_alter = [],
		name_eng = "Canada",
		part_sample = "AM",
		post_location = "CANC",
		url_app = "a/ca",
		url_retail = "/ca",
		url_store = "/ca",
		url_taa = "/ca"
	),
	Region(
		flag = "🇨🇭",
		abbr = "CH",
		job_code = {
			"ch-business-expert-m-f-d": 114438007,
			"ch-business-pro-m-f-d": 200125441,
			"ch-creative-m-f-d": 114438008,
			"ch-expert-m-f-d": 114438009,
			"ch-genius-m-f-d": 114438010,
			"ch-operations-expert-m-f-d": 114438011,
			"ch-specialist-m-f-d": 114438017,
			"ch-technical-specialist-m-f-d": 114438204
		},
		locale = "fr_CH",
		name = "瑞士",
		name_alter = [
			"Swiss",
			"Suisse"
		],
		name_eng = "Switzerland",
		part_sample = "ZM",
		post_location = "CHEC",
		url_app = "e/ch-fr",
		url_retail = "/chfr",
		url_store = "/ch-fr",
		url_taa = "/chfr"
	),
	Region(
		flag = "🇨🇳",
		abbr = "CN",
		job_code = {
			"cn-business-expert": 114438020,
			"cn-business-pro": 200125389,
			"cn-creative": 114438021,
			"cn-expert": 114438022,
			"cn-genius": 114438023,
			"cn-manager": 114438027,
			"cn-operations-expert": 114438024,
			"cn-senior-manager": 114438255,
			"cn-specialist": 114438030,
			"cn-store-leader": 114438029,
			"cn-technical-specialist": 114438189
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
		post_location = "CHNC",
		url_app = "p/cn",
		url_retail = ".cn",
		url_store = ".cn",
		url_taa = "/cn"
	),
	Region(
		flag = "🇩🇪",
		abbr = "DE",
		job_code = {
			"de-business-expert-m-f-d": 114438033,
			"de-business-pro-m-f-d": 200125393,
			"de-creative-m-f-d": 114438034,
			"de-expert-m-f-d": 114438035,
			"de-genius-m-f-d": 114438036,
			"de-operations-expert-m-f-d": 114438037,
			"de-specialist-m-f-d": 114438043,
			"de-technical-specialist-m-f-d": 114438207
		},
		locale = "de_DE",
		name = "德国",
		name_alter = [
			"德國",
			"Deutschland"
		],
		name_eng = "Germany",
		part_sample = "ZM",
		post_location = "DEU",
		url_app = "e/de",
		url_retail = "/de",
		url_store = "/de",
		url_taa = "/de"
	),
	Region(
		flag = "🇪🇸",
		abbr = "ES",
		job_code = {
			"es-business-expert": 114438046,
			"es-business-pro": 200125431,
			"es-creative": 114438047,
			"es-expert": 114438048,
			"es-genius": 114438049,
			"es-operations-expert": 114438050,
			"es-specialist": 114438056,
			"es-technical-specialist": 114438212
		},
		locale = "es_ES",
		name = "西班牙",
		name_alter = [
			"España"
		],
		name_eng = "Spain",
		part_sample = "ZM",
		post_location = "ESPC",
		url_app = "e/es",
		url_retail = "/es",
		url_store = "/es",
		url_taa = "/es"
	),
	Region(
		flag = "🇫🇷",
		abbr = "FR",
		job_code = {
			"fr-business-expert": 114438059,
			"fr-business-pro": 200125391,
			"fr-creative": 114438060,
			"fr-expert": 114438061,
			"fr-genius": 114438062,
			"fr-operations-expert": 114438063,
			"fr-specialist": 114438069,
			"fr-technical-specialist": 114438206
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
		post_location = "FRAC",
		url_app = "e/fr",
		url_retail = "/fr",
		url_store = "/fr",
		url_taa = "/fr"
	),
	Region(
		flag = "🇬🇧",
		abbr = "GB",
		job_code = {
			"uk-business-expert": 114438135,
			"uk-business-pro": 200125450,
			"uk-creative": 114438136,
			"uk-expert": 114438137,
			"uk-genius": 114438138,
			"uk-specialist": 114438145,
			"uk-technical-specialist": 114438202
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
		post_location = "GBR",
		url_app = "e/uk",
		url_retail = "/uk",
		url_store = "/uk",
		url_taa = "/uk"
	),
	Region(
		flag = "🇭🇰",
		abbr = "HK",
		job_code = {
			"hk-business-expert": 114438072,
			"hk-business-pro": 200125406,
			"hk-creative": 114438073,
			"hk-expert": 114438074,
			"hk-genius": 114438075,
			"hk-manager": 114438079,
			"hk-operations-expert": 114438076,
			"hk-specialist": 114438082,
			"hk-technical-specialist": 114438208
		},
		locale = "zh_HK",
		name = "香港",
		name_alter = [
			"香港特别行政区",
			"香港特別行政區"
		],
		name_eng = "Hong Kong",
		part_sample = "FE",
		post_location = "HKGC",
		url_app = "p/hk-zh",
		url_retail = "/hk",
		url_store = "/hk-zh",
		url_taa = "/hk"
	),
	Region(
		flag = "🇮🇳",
		abbr = "IN",
		job_code = {
			"in-business-expert": 200313970,
			"in-business-pro": 200314003,
			"in-creative": 200313991,
			"in-expert": 200314010,
			"in-genius": 200314015,
			"in-operations-expert": 200314033,
			"in-specialist": 200314117,
			"in-technical-specialist": 200314122
		},
		locale = "en_IN",
		name = "印度",
		name_alter = [],
		name_eng = "India",
		part_sample = "ZM",
		post_location = "INDC",
		url_app = None,
		url_retail = "/in",
		url_store = "/in",
		url_taa = "/in"
	),
	Region(
		flag = "🇮🇹",
		abbr = "IT",
		job_code = {
			"it-business-expert": 114438085,
			"it-business-pro": 200125410,
			"it-creative": 114438086,
			"it-expert": 114438087,
			"it-genius": 114438088,
			"it-operations-expert": 114438089,
			"it-specialist": 114438095,
			"it-technical-specialist": 114438209
		},
		locale = "it_IT",
		name = "意大利",
		name_alter = [
			"Italia",
			"义大利"
		],
		name_eng = "Italy",
		part_sample = "ZM",
		post_location = "ITAC",
		url_app = "e/it",
		url_retail = "/it",
		url_store = "/it",
		url_taa = "/it"
	),
	Region(
		flag = "🇯🇵",
		abbr = "JP",
		job_code = {
			"jp-specialist": 114438107
		},
		locale = "ja_JP",
		name = "日本",
		name_alter = [],
		name_eng = "Japan",
		part_sample = "FE",
		post_location = "JPNC",
		url_app = "j/jp",
		url_retail = "/jp",
		url_store = "/jp",
		url_taa = "/jp"
	),
	Region(
		flag = "🇰🇷",
		abbr = "KR",
		job_code = {
			"kr-manager": 114438322,
			"kr-senior-manager": 114438327,
			"kr-specialist": 114438326,
			"kr-store-leader": 114438324
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
		post_location = "KOR",
		url_app = "p/kr",
		url_retail = "/kr",
		url_store = "/kr",
		url_taa = "/kr"
	),
	Region(
		flag = "🇲🇴",
		abbr = "MO",
		job_code = {
			"mo-business-expert": 114438273,
			"mo-business-pro": 200125420,
			"mo-creative": 114438274,
			"mo-expert": 114438275,
			"mo-genius": 114438276,
			"mo-operations-expert": 114438277,
			"mo-specialist": 114438282,
			"mo-technical-specialist": 114438281
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
		post_location = "MAC",
		url_app = None,
		url_retail = "/mo",
		url_store = None,
		url_taa = "/mo"
	),
	Region(
		flag = "🇲🇽",
		abbr = "MX",
		job_code = {
			"mx-business-expert": 114438292,
			"mx-business-pro": 200125422,
			"mx-creative": 114438295,
			"mx-expert": 114438290,
			"mx-genius": 114438291,
			"mx-operations-expert": 114438285,
			"mx-specialist": 114438297,
			"mx-technical-specialist": 114438287
		},
		locale = "es_MX",
		name = "墨西哥",
		name_alter = [],
		name_eng = "Mexico",
		part_sample = "AM",
		post_location = "MEXC",
		url_app = "a/mx",
		url_retail = "/mx",
		url_store = "/mx",
		url_taa = "/mx"
	),
	Region(
		flag = "🇲🇾",
		abbr = "MY",
		job_code = {
			"my-business-expert": 200450011,
			"my-business-pro": 200450016,
			"my-creative": 200449996,
			"my-expert": 200450004,
			"my-genius": 200450000,
			"my-operations-expert": 200450018,
			"my-specialist": 200450003,
			"my-technical-specialist": 200450008
		},
		locale = "en_MY",
		name = "马来西亚",
		name_alter = [
			"馬來西亞",
			"大马"
		],
		name_eng = "Malaysia",
		part_sample = "FE",
		post_location = "MYS",
		url_app = "p/my",
		url_retail = "/my",
		url_store = "/my",
		url_taa = "/my"
	),
	Region(
		flag = "🇳🇱",
		abbr = "NL",
		job_code = {
			"nl-business-expert": 114438109,
			"nl-business-pro": 200125427,
			"nl-creative": 114438110,
			"nl-expert": 114438111,
			"nl-genius": 114438112,
			"nl-operations-expert": 114438113,
			"nl-specialist": 114438119,
			"nl-technical-specialist": 114438211
		},
		locale = "nl_NL",
		name = "荷兰",
		name_alter = [
			"荷蘭",
			"Holland"
		],
		name_eng = "Netherlands",
		part_sample = "ZM",
		post_location = "NLD",
		url_app = "e/nl",
		url_retail = "/nl",
		url_store = "/nl",
		url_taa = "/nl"
	),
	Region(
		flag = "🇸🇪",
		abbr = "SE",
		job_code = {
			"se-business-expert": 114438122,
			"se-business-pro": 200125435,
			"se-creative": 114438123,
			"se-expert": 114438124,
			"se-genius": 114438125,
			"se-operations-expert": 114438126,
			"se-specialist": 114438132,
			"se-technical-specialist": 114438205
		},
		locale = "sv_SE",
		name = "瑞典",
		name_alter = [],
		name_eng = "Sweden",
		part_sample = "ZM",
		post_location = "SWEC",
		url_app = "e/se",
		url_retail = "/se",
		url_store = "/se",
		url_taa = "/se"
	),
	Region(
		flag = "🇸🇬",
		abbr = "SG",
		job_code = {
			"sg-specialist": 114438238
		},
		locale = "en_SG",
		name = "新加坡",
		name_alter = [
			"星加坡"
		],
		name_eng = "Singapore",
		part_sample = "FE",
		post_location = "SGP",
		url_app = "p/sg",
		url_retail = "/sg",
		url_store = "/sg",
		url_taa = "/sg"
	),
	Region(
		flag = "🇹🇭",
		abbr = "TH",
		job_code = {
			"th-specialist": 114438346
		},
		locale = "th_TH",
		name = "泰国",
		name_alter = [
			"泰國"
		],
		name_eng = "Thailand",
		part_sample = "FE",
		post_location = "THA",
		url_app = "p/th-en",
		url_retail = "/th",
		url_store = "/th",
		url_taa = "/th"
	),
	Region(
		flag = "🇹🇷",
		abbr = "TR",
		job_code = {
			"tr-business-expert": 114438163,
			"tr-creative": 114438167,
			"tr-expert": 114438165,
			"tr-genius": 114438166,
			"tr-operations-expert": 114438168,
			"tr-specialist": 114438164,
			"tr-technical-specialist": 114438203
		},
		locale = "tr_TR",
		name = "土耳其",
		name_alter = [],
		name_eng = "Turkey",
		part_sample = "ZM",
		post_location = "TURC",
		url_app = "e/tr",
		url_retail = "/tr",
		url_store = "/tr",
		url_taa = "/tr"
	),
	Region(
		flag = "🇹🇼",
		abbr = "TW",
		job_code = {
			"tw-business-expert": 114438303,
			"tw-business-pro": 200125447,
			"tw-creative": 114438314,
			"tw-expert": 114438305,
			"tw-genius": 114438306,
			"tw-operations-expert": 114438307,
			"tw-specialist": 114438311,
			"tw-technical-specialist": 114438313
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
		post_location = "TWN",
		url_app = "p/tw",
		url_retail = "/tw",
		url_store = "/tw",
		url_taa = "/tw"
	),
	Region(
		flag = "🇺🇸",
		abbr = "US",
		job_code = {
			"us-business-expert": 114438148,
			"us-business-pro": 200125453,
			"us-creative": 114438149,
			"us-expert": 114438150,
			"us-genius": 114438151,
			"us-operations-expert": 114438152,
			"us-specialist": 114438158,
			"us-technical-specialist": 114438201
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
		post_location = "USA",
		url_app = "a/us",
		url_retail = "",
		url_store = "",
		url_taa = ""
	)
]

Regions = {r.flag: r for r in RegionList}