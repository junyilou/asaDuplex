import os, json, time, IFTTT
from retailData import stateCHN, stateCode, stateEmoji, specialistCode

rpath, wAns = os.path.expanduser('~') + "/Retail/Jobs/", ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"
#stateCHN, stateCode, stateEmoji, specialistCode = ["澳大利亚"], ["AU"], ["🇦🇺"], [7991] #Debug

wAns = ""; mOpen = open(rpath + "savedJobs"); mark = mOpen.read(); mOpen.close()
for scn, scd, ste, spl in zip(stateCHN, stateCode, stateEmoji, specialistCode):
	realCode = "11443" + str(spl)
	savename = rpath + scd + "/state.json"
	while True:
		os.system("wget -q -t 100 -T 5 -O " + savename + " https://jobs.apple.com/api" + 
		"/v1/jobDetails/PIPE-" + realCode + "/stateProvinceList")
		if os.path.getsize(savename) > 0: break
	jOpen = open(savename); jRead = jOpen.read(); jOpen.close()
	if "Maintenance" in jRead: 
		print("遇到了 Apple 招聘页面维护"); break
	stateJSON = json.loads(jRead)["searchResults"]
	for i in stateJSON: 
		savename = rpath + scd + "/location_" + i["id"].replace("postLocation-", "") + ".json"
		print("Downloading: " + i["id"] + " for " + scn)
		while True:
			os.system("wget -q -t 100 -T 5 -O " + savename + " 'https://jobs.apple.com/api/v1/jobDetails/PIPE-" 
			+ realCode + "/storeLocations?searchField=stateProvince&fieldValue=" + i["id"] + "'")
			if os.path.getsize(savename) > 0: break
	for j in stateJSON: 
		savename = rpath + scd + "/location_" + j["id"].replace("postLocation-", "") + ".json"
		jOpen = open(savename); jRead = jOpen.read(); jOpen.close()
		if "Maintenance" in jRead: 
			print("遇到了 Apple 招聘页面维护"); break
		cityJSON = json.loads(jRead)
		for c in cityJSON:
			rolloutCode = c["code"]
			if not rolloutCode in mark:
				wAns += ste + rolloutCode + ", "
				pushAns = ("新店新机遇: " + ste + scn + "新增招聘地点 " + c["name"]
				+ ", 代号 " + rolloutCode + ", 文件名 " + j["id"].replace("postLocation-", "") + ".json"); print(pushAns)
				IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", IFTTT.getkey(), 0)
if wAns != "":
	mWrite = open(rpath + "savedJobs", "w"); mWrite.write(mark + wAns); mWrite.close()
print(time.strftime("%F %T", time.localtime()))