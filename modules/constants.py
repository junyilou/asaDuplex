userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"}

partRuleBase = r"[FGHMNPS][0-9A-Z]{3}[0-9]"
partRuleFull = r".*([FGHMNPS][0-9A-Z]{3}[0-9][A-Z]{1,2}/[A-Z]).*"
partRuleCheck = r".*([FGHMNPS][0-9A-Z]{3}[0-9]([A-Z]{1,2}/[A-Z])?).*"
partSpecialProduct = r".*(Z[0-9A-Z]{3}&(.*)?).*"

DIFFhead = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIFF HEAD</title>
</head>

<body><pre><code>\n"""
DIFFfoot = "</code></pre></body></html>"

editStart = "### *** EDIT START *** ###\n"
editEnd   = "\n### *** EDIT  END  *** ###"

allRegions = {
  "🇹🇷": {
    "name": "土耳其",
    "nameEng": "Turkey",
    "abbr": "TR",
    "mobileApp": "e/tr",
    "storeURL": "/tr",
    "shopURL": "/tr",
    "rootPath": "/tr",
    "rspLocale": "tr_TR",
    "partSample": "ZM",
    "jobCode": "114438164",
    "altername": [
      "Türkiye"
    ]
  },
  "🇦🇪": {
    "name": "阿联酋",
    "nameEng": "United Arab Emirates",
    "abbr": "AE",
    "mobileApp": "e/ae",
    "storeURL": "/ae",
    "shopURL": "/ae",
    "rootPath": "/ae",
    "rspLocale": "en_AE",
    "partSample": "ZE",
    "jobCode": "114438225",
    "altername": [
      "UAE",
      "阿拉伯联合酋长国",
      "阿拉伯联合大公国"
    ]
  },
  "🇬🇧": {
    "name": "英国",
    "nameEng": "United Kingdom",
    "abbr": "GB",
    "mobileApp": "e/uk",
    "storeURL": "/uk",
    "shopURL": "/uk",
    "rootPath": "/uk",
    "rspLocale": "en_GB",
    "partSample": "ZM",
    "jobCode": "114438145",
    "altername": [
      "UK",
      "Great Britain",
      "大英帝国"
    ]
  },
  "🇩🇪": {
    "name": "德国",
    "nameEng": "Germany",
    "abbr": "DE",
    "mobileApp": "e/de",
    "storeURL": "/de",
    "shopURL": "/de",
    "rootPath": "/de",
    "rspLocale": "de_DE",
    "partSample": "ZM",
    "jobCode": "114438043",
    "altername": [
      "Deutschland"
    ]
  },
  "🇹🇼": {
    "name": "台湾",
    "nameEng": "Taiwan",
    "abbr": "TW",
    "mobileApp": "p/tw",
    "storeURL": "/tw",
    "shopURL": "/tw",
    "rootPath": "/tw",
    "rspLocale": "zh_TW",
    "partSample": "FE",
    "jobCode": "114438311",
    "altername": [
      "ROC"
    ]
  },
  "TW": {
    "name": "台湾",
    "nameEng": "Taiwan",
    "abbr": "TW",
    "mobileApp": "p/tw",
    "storeURL": "/tw",
    "shopURL": "/tw",
    "rootPath": "/tw",
    "rspLocale": "zh_TW",
    "partSample": "FE",
    "jobCode": "114438311",
    "altername": [
      "ROC"
    ]
  },
  "🇺🇸": {
    "name": "美国",
    "nameEng": "United States",
    "abbr": "US",
    "mobileApp": "a/us",
    "storeURL": "",
    "shopURL": "",
    "rootPath": "",
    "rspLocale": "en_US",
    "partSample": "AM",
    "jobCode": "114438158",
    "altername": [
      "America",
      "U.S."
    ]
  },
  "🇲🇽": {
    "name": "墨西哥",
    "nameEng": "Mexico",
    "abbr": "MX",
    "mobileApp": "a/mx",
    "storeURL": "/mx",
    "shopURL": "/mx",
    "rootPath": "/mx",
    "rspLocale": "es_MX",
    "partSample": "AM",
    "jobCode": "114438297",
    "altername": []
  },
  "🇨🇭": {
    "name": "瑞士",
    "nameEng": "Switzerland",
    "abbr": "CH",
    "mobileApp": "e/ch-de",
    "storeURL": "/chde",
    "shopURL": "/ch-de",
    "rootPath": "/chde",
    "rspLocale": "de_CH",
    "partSample": "ZM",
    "jobCode": "114438017",
    "altername": [
      "Swiss"
    ]
  },
  "🇧🇪": {
    "name": "比利时",
    "nameEng": "Belgium",
    "abbr": "BE",
    "mobileApp": "e/be-fr",
    "storeURL": "/befr",
    "shopURL": "/be-fr",
    "rootPath": "/befr",
    "rspLocale": "fr_BE",
    "partSample": "ZM",
    "jobCode": "114438251",
    "altername": []
  },
  "🇳🇱": {
    "name": "荷兰",
    "nameEng": "Netherlands",
    "abbr": "NL",
    "mobileApp": "e/nl",
    "storeURL": "/nl",
    "shopURL": "/nl",
    "rootPath": "/nl",
    "rspLocale": "nl_NL",
    "partSample": "ZM",
    "jobCode": "114438119",
    "altername": [
      "Holland"
    ]
  },
  "🇪🇸": {
    "name": "西班牙",
    "nameEng": "Spain",
    "abbr": "ES",
    "mobileApp": "e/es",
    "storeURL": "/es",
    "shopURL": "/es",
    "rootPath": "/es",
    "rspLocale": "es_ES",
    "partSample": "ZM",
    "jobCode": "114438056",
    "altername": [
      "España"
    ]
  },
  "🇭🇰": {
    "name": "香港",
    "nameEng": "Hong Kong",
    "abbr": "HK",
    "mobileApp": "p/hk-zh",
    "storeURL": "/hk",
    "shopURL": "/hk",
    "rootPath": "/hk",
    "rspLocale": "zh_HK",
    "partSample": "FE",
    "jobCode": "114438082",
    "altername": []
  },
  "🇸🇪": {
    "name": "瑞典",
    "nameEng": "Sweden",
    "abbr": "SE",
    "mobileApp": "e/se",
    "storeURL": "/se",
    "shopURL": "/se",
    "rootPath": "/se",
    "rspLocale": "sv_SE",
    "partSample": "ZM",
    "jobCode": "114438132",
    "altername": []
  },
  "🇨🇳": {
    "name": "中国",
    "nameEng": "China",
    "abbr": "CN",
    "mobileApp": "p/cn",
    "storeURL": ".cn",
    "shopURL": ".cn",
    "rootPath": "/cn",
    "rspLocale": "zh_CN",
    "partSample": "FE",
    "jobCode": "114438030",
    "altername": [
      "PRC"
    ]
  },
  "🇫🇷": {
    "name": "法国",
    "nameEng": "France",
    "abbr": "FR",
    "mobileApp": "e/fr",
    "storeURL": "/fr",
    "shopURL": "/fr",
    "rootPath": "/fr",
    "rspLocale": "fr_FR",
    "partSample": "ZM",
    "jobCode": "114438069",
    "altername": []
  },
  "🇦🇺": {
    "name": "澳大利亚",
    "nameEng": "Australia",
    "abbr": "AU",
    "mobileApp": "p/au",
    "storeURL": "/au",
    "shopURL": "/au",
    "rootPath": "/au",
    "rspLocale": "en_AU",
    "partSample": "FE",
    "jobCode": "114437991",
    "altername": [
      "澳洲"
    ]
  },
  "🇮🇹": {
    "name": "意大利",
    "nameEng": "Italy",
    "abbr": "IT",
    "mobileApp": "e/it",
    "storeURL": "/it",
    "shopURL": "/it",
    "rootPath": "/it",
    "rspLocale": "it_IT",
    "partSample": "ZM",
    "jobCode": "114438095",
    "altername": [
      "Italia",
      "义大利"
    ]
  },
  "🇲🇴": {
    "name": "澳门",
    "nameEng": "Macau",
    "abbr": "MO",
    "mobileApp": None,
    "storeURL": "/mo",
    "shopURL": None,
    "rootPath": "/mo",
    "rspLocale": "zh_MO",
    "partSample": None,
    "jobCode": "114438282",
    "altername": [
      "Macao"
    ]
  },
  "🇧🇷": {
    "name": "巴西",
    "nameEng": "Brazil",
    "abbr": "BR",
    "mobileApp": "a/br",
    "storeURL": "/br",
    "shopURL": "/br",
    "rootPath": "/br",
    "rspLocale": "pt_BR",
    "partSample": "AM",
    "jobCode": "114438176",
    "altername": []
  },
  "🇯🇵": {
    "name": "日本",
    "nameEng": "Japan",
    "abbr": "JP",
    "mobileApp": "j/jp",
    "storeURL": "/jp",
    "shopURL": "/jp",
    "rootPath": "/jp",
    "rspLocale": "ja_JP",
    "partSample": "FE",
    "jobCode": "114438107",
    "altername": []
  },
  "🇰🇷": {
    "name": "韩国",
    "nameEng": "South Korea",
    "abbr": "KR",
    "mobileApp": "p/kr",
    "storeURL": "/kr",
    "shopURL": "/kr",
    "rootPath": "/kr",
    "rspLocale": "ko_KR",
    "partSample": "FE",
    "jobCode": "114438326",
    "altername": [
      "ROK",
      "南韩",
      "大韩民国"
    ]
  },
  "🇨🇦": {
    "name": "加拿大",
    "nameEng": "Canada",
    "abbr": "CA",
    "mobileApp": "a/ca",
    "storeURL": "/ca",
    "shopURL": "/ca",
    "rootPath": "/ca",
    "rspLocale": "en_CA",
    "partSample": "AM",
    "jobCode": "114438004",
    "altername": []
  },
  "🇦🇹": {
    "name": "奥地利",
    "nameEng": "Austria",
    "abbr": "AT",
    "mobileApp": "e/at",
    "storeURL": "/at",
    "shopURL": "/at",
    "rootPath": "/at",
    "rspLocale": "de_AT",
    "partSample": "ZM",
    "jobCode": "114438333",
    "altername": []
  },
  "🇸🇬": {
    "name": "新加坡",
    "nameEng": "Singapore",
    "abbr": "SG",
    "mobileApp": "p/sg",
    "storeURL": "/sg",
    "shopURL": "/sg",
    "rootPath": "/sg",
    "rspLocale": "en_SG",
    "partSample": "FE",
    "jobCode": "114438238",
    "altername": [
      "星加坡"
    ]
  },
  "🇹🇭": {
    "name": "泰国",
    "nameEng": "Thailand",
    "abbr": "TH",
    "mobileApp": "p/th-en",
    "storeURL": "/th",
    "shopURL": "/th",
    "rootPath": "/th",
    "rspLocale": "th_TH",
    "partSample": "FE",
    "jobCode": "114438346",
    "altername": []
  },
  "🇮🇳": {
    "name": "印度",
    "nameEng": "India",
    "abbr": "IN",
    "mobileApp": None,
    "storeURL": "/in",
    "shopURL": "/in",
    "rootPath": "/in",
    "rspLocale": "en_IN",
    "partSample": "ZM",
    "jobCode": "200314117",
    "altername": []
  }
}