import json, requests, time
requests.packages.urllib3.disable_warnings()

def DieterInfo(rtl):
	if type(rtl) == int:
		rtl = f"{rtl:0>3d}"
	rtl = rtl.replace("R", "")
	with open("Retail/storeInfo.json") as s:
		storejson = json.loads(s.read())
	try: 
		rname = storejson['name'][rtl]
		rflag = storejson['flag'][rtl] + " "
	except KeyError: 
		rname = "Store"; rflag = ""
	try:
		rnso = storejson['nso'][rtl]
		rnso = ", 首次开幕于 " + time.strftime("%Y 年 %-m 月 %-d 日", time.strptime(rnso, "%Y-%m-%d"))
	except KeyError:
		rnso = ""
	tellRaw = f"#图片更新 #标签 {rflag}Apple {rname}, R{rtl}{rnso}"
	return tellRaw

def DieterHeader(rtl):
	if type(rtl) == int:
		rtl = f"{rtl:0>3d}"
	rtl = rtl.replace("R", "")
	r = requests.head(f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{rtl}.png", 
		allow_redirects = True, verify = False)
	return "404" if r.status_code == 404 else r.headers['Last-Modified']