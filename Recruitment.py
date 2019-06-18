#-*- coding:utf-8 -*-
import json, os, sys, time, IFTTT, retailData

rpath = os.path.expanduser('~') + "/Retail/Jobs/"; wAns = ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop.jpg"

stateCHN = retailData.stateCHN; stateCode = retailData.stateCode
stateEmoji = retailData.stateEmoji; specialistCode = retailData.specialistCode
#stateCHN = ["澳大利亚"]; stateCode = ["AU"]; stateEmoji = ["🇦🇺"]; specialistCode = [7991] #Debug

masterKey = IFTTT.getkey()

while True:
	wAns = ""; mOpen = open(rpath + "savedJobs"); mark = mOpen.read(); mOpen.close()
	for adpre in range(0, len(specialistCode)):
		reload(sys); sys.setdefaultencoding('utf-8')
		realCode = "11443" + str(specialistCode[adpre])
		savename = rpath + stateCode[adpre] + "/state.json"
		while True:
			os.system("wget -q -t 100 -T 5 -O " + savename + " https://jobs.apple.com/api" + 
			"/v1/jobDetails/PIPE-" + realCode + "/stateProvinceList")
			if os.path.getsize(savename) > 0: break
		jOpen = open(savename); stateJSON = json.loads(jOpen.read())["searchResults"]; jOpen.close()
		print "                                                  \r", #Pre Scheme
		sys.stdout.flush()
		for i in range(0, len(stateJSON)): 
			dID = stateJSON[i]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + dID.replace("postLocation-", "") + ".json"
			header = "[" + str(adpre + 1) + "/" + str(len(specialistCode)) + "] "
			statusBar = "正在下载" + stateCHN[adpre] + "的城市文件, 已完成 " + str((i + 1) * 100 / len(stateJSON))
			print header + statusBar + "% \r",
			sys.stdout.flush()
			while True:
				os.system("wget -q -t 100 -T 5 -O " + savename + " 'https://jobs.apple.com/api/v1/jobDetails/PIPE-" 
				+ realCode + "/storeLocations?searchField=stateProvince&fieldValue=" + dID + "'")
				if os.path.getsize(savename) > 0: break
		for j in range(0, len(stateJSON)): 
			oID = stateJSON[j]["id"]
			savename = rpath + stateCode[adpre] + "/location_" + oID.replace("postLocation-", "") + ".json"
			cityJSON = json.loads(open(savename).read().decode('utf-8-sig'))
			for c in range(0, len(cityJSON)):
				rolloutCode = cityJSON[c]["code"]
				if not rolloutCode in mark:
					wAns += stateEmoji[adpre] + rolloutCode + ", "
					pushAns = "新店新机遇: " + stateEmoji[adpre] + stateCHN[adpre] + "新增招聘地点 " + cityJSON[c]["name"]
					pushAns += ", 代号 " + rolloutCode + ", 文件名 " + oID.replace("postLocation-", "") + ".json"
					IFTTT.pushbots(pushAns, "Apple 招贤纳才", imageURL, "raw", masterKey, 0)
	mWrite = open(rpath + "savedJobs", "w"); mWrite.write(mark + wAns); mWrite.close(); print 
	print time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	time.sleep(43200)