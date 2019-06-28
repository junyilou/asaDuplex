#-*- coding:utf-8 -*-
import os, urllib2, sys, json, time, IFTTT, retailData

filename, cityname = retailData.filename, retailData.cityname
#filename, cityname = ['qibao', 'apmhongkong', 'xinyia13'], ['@上海', '#香港', '&台湾'] #Debug
num, allMainlandChina = len(filename), ""
for rep in range(num): 
	cityname[rep] = cityname[rep].replace("@", "🇨🇳").replace("#", "🇭🇰").replace("$", "🇲🇴").replace("&", "🇹🇼")
allMainlandChina = "、".join(cityname[:42])

def down(fname, region): 
	os.system("wget -q -t 100 -T 3 -O " + rpath + fname + ".json --no-check-certificate " +
	"'https://www.apple.com/today-bff/landing/store?stageRootPath=/"+ region + "&storeSlug=" + fname + "'")
def home():
	wAns = ""; mOpen = open(rpath + "savedEvent.txt"); mark = mOpen.read(); mOpen.close()
	for d in range(num):
		cdsize = 0
		while cdsize == 0:
			if cityname[d][:8] == "🇨🇳": down(filename[d], "cn")
			if cityname[d][:8] == "🇭🇰": down(filename[d], "hk")
			if cityname[d][:8] == "🇲🇴": down(filename[d], "mo")
			if cityname[d][:8] == "🇹🇼": down(filename[d], "tw")
			cdsize = os.path.getsize(rpath + filename[d] + ".json")
		print "Download in Progress: " + str((d + 1) * 100 / num) + "%\r",
		sys.stdout.flush()
	print
	for i in range(num):
		rOpen = open(rpath + filename[i] + ".json"); isMulti = False
		raw = rOpen.read(); rJson = json.loads(json.dumps(json.loads(raw)).replace("\u2060", ""))
		rJson = rJson["courses"]; rOpen.close()
		for rTitle in rJson:
			rCourse = rJson[rTitle]; singleName = rCourse["name"]
			if not singleName in mark and not singleName in wAns: 
				wAns += singleName + ",\n"; citAns = cityname[i]
				for r in range(i, num):
					eOpen = open(rpath + filename[r] + ".json"); eAns = eOpen.read()
					eJson = json.loads(json.dumps(json.loads(eAns)).replace("\u2060", ""))
					eJson = eJson["courses"]; eOpen.close()
					for eTitle in eJson:
						eCourse = eJson[eTitle]; checkAns = cityname[r].replace("🇨🇳", "").replace("🇭🇰", "")
						checkAns = checkAns.replace("🇲🇴", "").replace("🇹🇼", "")
						if eCourse["name"] == singleName and not checkAns in citAns:
							citAns += "、" + cityname[r]
				citAns = citAns.replace(allMainlandChina, "🇨🇳中国大陆")
				pushAns = "#TodayatApple " + citAns + "有新活动: " + singleName
				if citAns.count("🇨🇳") > 1: pushAns = pushAns.replace("🇨🇳", "").replace("#TodayatApple ", "#TodayatApple 🇨🇳")
				pushAns = pushAns.replace('"', "").replace("'", "").replace("：", " - ")
				print pushAns
				pictureURL = rCourse["backgroundMedia"]["images"][0]["landscape"]["source"] + "?output-format=jpg"
				IFTTT.pushbots(pushAns, "Today at Apple 新活动", pictureURL, "raw", masterKey, 0)
		print "Compare in Progress: " + str((i + 1) * 100 / num) + "%\r",
		sys.stdout.flush()
	mWrite = open(rpath + "savedEvent.txt", "w"); mWrite.write(mark + wAns); mWrite.close(); print

masterKey = IFTTT.getkey()
rpath = os.path.expanduser('~') + "/Retail/"

while True:
	reload(sys); sys.setdefaultencoding('utf-8'); home()
	for rm in range(num): os.system("rm " + rpath + filename[rm] + ".json")
	print time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	time.sleep(10800)