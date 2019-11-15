import os, sys, json, time, IFTTT, PID
from retailData import filename, cityname

#filename, cityname = ['qibao', 'apmhongkong', 'xinyia13'], ['@上海', '#香港', '&台湾'] #Debug
num, allMainlandChina = len(filename), ""
for rep in range(num): 
	cityname[rep] = cityname[rep].replace("@", "🇨🇳").replace("#", "🇭🇰").replace("$", "🇲🇴").replace("&", "🇹🇼")

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
		print("正在下载 已完成 " + str(int((d + 1) * 100 / num)) + "%\r", end = "")
		sys.stdout.flush()
	print()
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
				IFTTT.pushbots(pushAns, "", pictureURL, "tech", IFTTT.getkey(), 0)
		print("正在比较 已完成 " + str(int((i + 1) * 100 / num)) + "%\r", end = "")
		sys.stdout.flush()
	mWrite = open(rpath + "savedEvent.txt", "w"); mWrite.write(mark + wAns); mWrite.close(); print()

PID.addCurrent(os.path.basename(__file__), os.getpid())
rpath = os.path.expanduser('~') + "/Retail/"

while True:
	home()
	for rm in range(num): os.system("rm " + rpath + filename[rm] + ".json")
	print(time.strftime("%F %T", time.localtime()))
	time.sleep(10800)