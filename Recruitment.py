import json, os, time, IFTTT
from retailData import stateCHN, stateCode, stateEmoji, specialistCode

rpath, wAns = os.path.expanduser('~') + "/Retail/Jobs/", ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"
#stateCHN, stateCode, stateEmoji, specialistCode = ["澳大利亚"], ["AU"], ["🇦🇺"], [7991] #Debug

def home():
	wAns = ""; mOpen = open(rpath + "savedJobs"); mark = mOpen.read(); mOpen.close()
	for adpre in range(len(specialistCode)):
		realCode = "11443" + str(specialistCode[adpre])
		savename = rpath + stateCode[adpre] + "/state.json"
		while True:
			os.system("wget -q -t 100 -T 5 -O " + savename + " https://jobs.apple.com/api" + 
			"/v1/jobDetails/PIPE-" + realCode + "/stateProvinceList")
			if os.path.getsize(savename) > 0: break
		jOpen = open(savename); jRead = jOpen.read(); jOpen.close()
		if "Maintenance" in jRead: 
			print("于 " + time.strftime("%-m 月 %-d 日 %-H:%M", time.localtime()) + " 遇到页面维护"); return
		stateJSON = json.loads(jRead)["searchResults"]
		for i in range(len(stateJSON)): 
			dID = stateJSON[i]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + dID.replace("postLocation-", "") + ".json"
			header = "[" + str(adpre + 1) + "/" + str(len(specialistCode)) + "] "
			statusBar = "正在下载" + stateCHN[adpre] + "的城市文件, 已完成 " + str(int((i + 1) * 100 / len(stateJSON)))
			print(header + statusBar)
			while True:
				os.system("wget -q -t 100 -T 5 -O " + savename + " 'https://jobs.apple.com/api/v1/jobDetails/PIPE-" 
				+ realCode + "/storeLocations?searchField=stateProvince&fieldValue=" + dID + "'")
				if os.path.getsize(savename) > 0: break
		for j in range(len(stateJSON)): 
			oID = stateJSON[j]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + oID.replace("postLocation-", "") + ".json"
			jOpen = open(savename); jRead = jOpen.read(); jOpen.close()
			if "Maintenance" in jRead: 
				print("于 " + time.strftime("%-m 月 %-d 日 %-H:%M", time.localtime()) + " 遇到页面维护"); return
			cityJSON = json.loads(jRead)
			for c in range(len(cityJSON)):
				rolloutCode = cityJSON[c]["code"]
				if not rolloutCode in mark:
					wAns += stateEmoji[adpre] + rolloutCode + ", "
					pushAns = ("新店新机遇: " + stateEmoji[adpre] + stateCHN[adpre] + "新增招聘地点 " + cityJSON[c]["name"]
					+ ", 代号 " + rolloutCode + ", 文件名 " + oID.replace("postLocation-", "") + ".json"); print(pushAns)
					IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", IFTTT.getkey(), 0)
	mWrite = open(rpath + "savedJobs", "w"); mWrite.write(mark + wAns); mWrite.close(); print()

home()
print(time.strftime("%F %T", time.localtime()))