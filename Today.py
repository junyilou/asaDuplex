import os, json, time, IFTTT
from retailData import filename, cityname

rpath = os.path.expanduser('~') + "/Retail/"; allChina = len(filename)
wAns = ""; mOpen = open(rpath + "savedEvent.txt"); mark = mOpen.read(); mOpen.close()

for fn in filename:
	os.system("wget -q -t 20 -T 3 -O " + rpath + fn + ".json --no-check-certificate " +
		"'https://www.apple.com/today-bff/landing/store?stageRootPath=/cn&storeSlug=" + fn + "'")
	print("Downloading schedule file: " + fn + ".json")

for fn, cyn in zip(filename, cityname):
	rOpen = open(rpath + fn + ".json")
	raw = rOpen.read(); rJson = json.loads(raw.replace("\u2060", ""))
	rJson = rJson["courses"]; rOpen.close()
	for rTitle in rJson:
		rCourse = rJson[rTitle]; singleName = rCourse["name"]
		if not singleName in mark and not singleName in wAns: 
			wAns += singleName + ",\n"; citAns = cyn
			for sn, csn in zip(filename, cityname):
				eOpen = open(rpath + sn + ".json"); eAns = eOpen.read()
				eJson = json.loads(eAns.replace("\u2060", ""))
				eJson = eJson["courses"]; eOpen.close()
				for eTitle in eJson:
					eCourse = eJson[eTitle]
					if eCourse["name"] == singleName and not csn in citAns:
						citAns += "、" + csn
			pushAns = "#TodayatApple " + citAns + "有新活动: " + singleName
			pushAns = pushAns.replace('"', "").replace("'", "").replace("：", " - ")
			print(pushAns)
			pictureURL = rCourse["backgroundMedia"]["images"][0]["landscape"]["source"]
			IFTTT.pushbots(pushAns, "", pictureURL, "tech", IFTTT.getkey()[0], 0)
mWrite = open(rpath + "savedEvent.txt", "w"); mWrite.write(mark + wAns); mWrite.close()
for rm in filename: os.system("rm " + rpath + rm + ".json")
print(time.strftime("%F %T", time.localtime()))