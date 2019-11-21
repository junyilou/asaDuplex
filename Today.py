import os, json, time, IFTTT
from retailData import filename, cityname

#filename, cityname = ['qibao', 'apmhongkong', 'xinyia13'], ['@上海', '#香港', '&台湾'] #Debug
num, allMainlandChina = len(filename), ""
for rep in range(num): 
	cityname[rep] = cityname[rep].replace("@", "🇨🇳").replace("#", "🇭🇰").replace("$", "🇲🇴").replace("&", "🇹🇼")

rpath = os.path.expanduser('~') + "/Retail/"

def down(fname, region): 
	os.system("wget -q -t 100 -T 3 -O " + rpath + fname + ".json --no-check-certificate " +
	"'https://www.apple.com/today-bff/landing/store?stageRootPath=/"+ region + "&storeSlug=" + fname + "'")

def home():
	wAns = ""; mOpen = open(rpath + "savedEvent.txt"); mark = mOpen.read(); mOpen.close()
	for d in range(num):
		cdsize = 0
		while cdsize == 0:
			if "🇨🇳" in cityname[d]: down(filename[d], "cn")
			if "🇭🇰" in cityname[d]: down(filename[d], "hk")
			if "🇲🇴" in cityname[d]: down(filename[d], "mo")
			if "🇹🇼" in cityname[d]: down(filename[d], "tw")
			cdsize = os.path.getsize(rpath + filename[d] + ".json")
		print("正在下载" + cityname[d] + "的活动时间表...")
	for i in range(num):
		rOpen = open(rpath + filename[i] + ".json"); isMulti = False
		raw = rOpen.read(); rJson = json.loads(raw.replace("\u2060", ""))
		rJson = rJson["courses"]; rOpen.close()
		for rTitle in rJson:
			rCourse = rJson[rTitle]; singleName = rCourse["name"]
			if not singleName in mark and not singleName in wAns: 
				wAns += singleName + ",\n"; citAns = cityname[i]
				for r in range(i, num):
					eOpen = open(rpath + filename[r] + ".json"); eAns = eOpen.read()
					eJson = json.loads(eAns.replace("\u2060", ""))
					eJson = eJson["courses"]; eOpen.close()
					for eTitle in eJson:
						eCourse = eJson[eTitle]; checkAns = cityname[r].replace("🇨🇳", "").replace("🇭🇰", "")
						checkAns = checkAns.replace("🇲🇴", "").replace("🇹🇼", "")
						if eCourse["name"] == singleName and not checkAns in citAns:
							citAns += "、" + cityname[r]
				pushAns = "#TodayatApple " + citAns + "有新活动: " + singleName
				if citAns.count("🇨🇳") > 1: pushAns = pushAns.replace("🇨🇳", "").replace("#TodayatApple ", "#TodayatApple 🇨🇳")
				pushAns = pushAns.replace('"', "").replace("'", "").replace("：", " - ")
				print(pushAns)
				pictureURL = rCourse["backgroundMedia"]["images"][0]["landscape"]["source"] + "?output-format=jpg"
				IFTTT.pushbots(pushAns, "", pictureURL, "tech", IFTTT.getkey()[0], 0)
	mWrite = open(rpath + "savedEvent.txt", "w"); mWrite.write(mark + wAns); mWrite.close()
	for rm in range(num): os.system("rm " + rpath + filename[rm] + ".json")

home()
print(time.strftime("%F %T", time.localtime()))