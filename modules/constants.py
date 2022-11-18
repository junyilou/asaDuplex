userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"}

partRuleBase = r"[FGHMNPS][0-9A-Z]{3}[0-9]"
partRuleFull = r"([FGHMNPS][0-9A-Z]{3}[0-9][A-Z]{1,2}/[A-Z])"
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

editStart = "### *** EDIT START *** ###\n"
editEnd   = "\n### *** EDIT  END  *** ###"

allRegions = {
  "HK": {
    "abbr": "HKEN",
    "altername": [],
    "jobCode": "114438082",
    "mobileApp": "p/hk",
    "name": "香港 (English)",
    "nameEng": "Hong Kong (English)",
    "partSample": "FE",
    "rootPath": "/hk/en",
    "rspLocale": "en_HK",
    "shopURL": "/hk",
    "storeURL": "/hk/en"
  },
  "TW": {
    "abbr": "TW",
    "altername": [
      "ROC",
      "中华民国"
    ],
    "jobCode": "114438311",
    "mobileApp": "p/tw",
    "name": "台湾",
    "nameEng": "Taiwan",
    "partSample": "FE",
    "rootPath": "/tw",
    "rspLocale": "zh_TW",
    "shopURL": "/tw",
    "storeURL": "/tw"
  },
  "🇦🇪": {
    "abbr": "AE",
    "altername": [
      "UAE",
      "阿拉伯联合酋长国",
      "阿拉伯联合大公国"
    ],
    "jobCode": "114438225",
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
    "jobCode": "114438333",
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
    "jobCode": "114437991",
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
    "altername": [],
    "jobCode": "114438251",
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
    "jobCode": "114438176",
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
    "jobCode": "114438004",
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
    "jobCode": "114438017",
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
      "PRC"
    ],
    "jobCode": "114438030",
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
      "Deutschland"
    ],
    "jobCode": "114438043",
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
    "jobCode": "114438056",
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
    "altername": [],
    "jobCode": "114438069",
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
      "大英帝国"
    ],
    "jobCode": "114438145",
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
    "altername": [],
    "jobCode": "114438082",
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
    "jobCode": "200314117",
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
    "jobCode": "114438095",
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
    "jobCode": "114438107",
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
      "大韩民国"
    ],
    "jobCode": "114438326",
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
      "Macao"
    ],
    "jobCode": "114438282",
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
    "jobCode": "114438297",
    "mobileApp": "a/mx",
    "name": "墨西哥",
    "nameEng": "Mexico",
    "partSample": "AM",
    "rootPath": "/mx",
    "rspLocale": "es_MX",
    "shopURL": "/mx",
    "storeURL": "/mx"
  },
  "🇳🇱": {
    "abbr": "NL",
    "altername": [
      "Holland"
    ],
    "jobCode": "114438119",
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
    "jobCode": "114438132",
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
    "jobCode": "114438238",
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
    "altername": [],
    "jobCode": "114438346",
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
    "altername": [
      "Türkiye"
    ],
    "jobCode": "114438164",
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
      "中华民国"
    ],
    "jobCode": "114438311",
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
      "America",
      "U.S."
    ],
    "jobCode": "114438158",
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