import json, os, sys, time, IFTTT, retailData, PID

rpath, wAns = os.path.expanduser('~') + "/Retail/Jobs/", ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"

stateCHN, stateCode = retailData.stateCHN, retailData.stateCode
stateEmoji, specialistCode = retailData.stateEmoji, retailData.specialistCode
#stateCHN, stateCode, stateEmoji, specialistCode = ["澳大利亚"], ["AU"], ["🇦🇺"], [7991] #Debug

PID.addCurrent(os.path.basename(__file__), os.getpid())

while True:
	wAns = ""; mOpen = open(rpath + "savedJobs"); mark = mOpen.read(); mOpen.close()
	for adpre in range(len(specialistCode)):
		realCode = "11443" + str(specialistCode[adpre])
		savename = rpath + stateCode[adpre] + "/state.json"
		while True:
			os.system("wget -q -t 100 -T 5 -O " + savename + " https://jobs.apple.com/api" + 
			"/v1/jobDetails/PIPE-" + realCode + "/stateProvinceList")
			if os.path.getsize(savename) > 0: break
		jOpen = open(savename)
		try: stateJSON = json.loads(jOpen.read())["searchResults"]; 
		except: print("在读取 stateJSON 的时候遇到了一些问题\n请尝试检查 Apple 官网服务状态或稍后再试\n"); exit()
		jOpen.close()
		print("                                                  \r", end = "") #Pre Scheme
		sys.stdout.flush()
		for i in range(len(stateJSON)): 
			dID = stateJSON[i]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + dID.replace("postLocation-", "") + ".json"
			header = "[" + str(adpre + 1) + "/" + str(len(specialistCode)) + "] "
			statusBar = "正在下载" + stateCHN[adpre] + "的城市文件, 已完成 " + str(int((i + 1) * 100 / len(stateJSON)))
			print(header + statusBar + "% \r", end = "")
			sys.stdout.flush()
			while True:
				os.system("wget -q -t 100 -T 5 -O " + savename + " 'https://jobs.apple.com/api/v1/jobDetails/PIPE-" 
				+ realCode + "/storeLocations?searchField=stateProvince&fieldValue=" + dID + "'")
				if os.path.getsize(savename) > 0: break
		for j in range(len(stateJSON)): 
			oID = stateJSON[j]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + oID.replace("postLocation-", "") + ".json"
			cityJSON = json.loads(open(savename).read())
			for c in range(len(cityJSON)):
				rolloutCode = cityJSON[c]["code"]
				if not rolloutCode in mark:
					wAns += stateEmoji[adpre] + rolloutCode + ", "
					pushAns = ("新店新机遇: " + stateEmoji[adpre] + stateCHN[adpre] + "新增招聘地点 " + cityJSON[c]["name"]
					+ ", 代号 " + rolloutCode + ", 文件名 " + oID.replace("postLocation-", "") + ".json")
					IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", IFTTT.getkey(), 0)
	mWrite = open(rpath + "savedJobs", "w"); mWrite.write(mark + wAns); mWrite.close(); print()
	print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
	time.sleep(43200)