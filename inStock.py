#-*- coding:utf-8 -*-
import os, json, sys, urllib2, time, IFTTT
from BeautifulSoup import BeautifulSoup

def title(partno):
	global savedName
	url = "https://www.apple.com/cn/shop/product/" + partno
	try: soup = BeautifulSoup(urllib2.urlopen(url, timeout = 20))
	except: savedName[partno] = "[获取产品名称出现错误]"
	else: savedName[partno] = soup.title.string.replace(" - Apple (中国大陆)", "").replace(" - Apple", "").replace("购买 ", "")

def productImage(partno):
	return ("https://as-images.apple.com/is/image/AppleInc/aos/published/images" 
		+ partno[0] + partno[:2] + "/" + partno + "/" + partno + "?fmt=png")

def fileOpen(fileloc):
	try: defOpen = open(fileloc); defReturn = defOpen.read(); defOpen.close()
	except IOError: return "No such file or directory."
	else: return defReturn

asaVersion = "5.4.1"
reload(sys); sys.setdefaultencoding('utf-8')
rpath = os.path.expanduser('~') + "/Retail/"
masterKey = IFTTT.getkey()

checkProduct = sys.argv[1:]; combProduct = ",".join(checkProduct)
alreadyAvailable = {}; singleProductOutput = {}; upb = ""; global savedName; savedName = {}
statesJSON = json.loads(fileOpen(rpath + "storeList.json"))["countryStateMapping"][0]["states"]
for j in range(0, len(checkProduct)): 
	alreadyAvailable[checkProduct[j]] = []; singleProductOutput[checkProduct[j]] = ""

while True:
	for s in range(0, len(statesJSON)):
		stateName = statesJSON[s]["stateName"]; storeJSON = statesJSON[s]["stores"]; stateStore = ""
		for t in range(0, len(storeJSON)):
			passCheck = 0; stateStore += storeJSON[t]["storeName"] + ", "
			for c in range(0, len(checkProduct)): 
				if storeJSON[t]["storeNumber"] in alreadyAvailable[checkProduct[c]]: passCheck += 1
			if passCheck == len(checkProduct): continue
			dLoc = rpath + "stock" + storeJSON[t]["storeNumber"]
			os.system("wget -t 100 -T 5 -q -O " + dLoc + " --header 'x-ma-pcmh: REL-" + asaVersion + 
				"' --header 'X-DeviceConfiguration: ss=2.00;vv=5.4.1;sv=12.3.1' " + 
				"'https://mobileapp.apple.com/mnr/p/cn/rci/rciCheckForPart?partNumber=" +
				combProduct + "&storeNumber=" + storeJSON[t]["storeNumber"] + "'")
			print "[" + str(s + 1) + "/" + str(len(statesJSON)) + "] Download in Progress: " + str((t + 1) * 100 / len(storeJSON)) + "%\r",
			sys.stdout.flush()
		print; stateStore = "】" + stateStore[:-2]
		for p in range(0, len(checkProduct)):
			availableStore = []
			for f in range(0, len(storeJSON)):
				try:
					stockJSON = json.loads(fileOpen(rpath + "stock" + storeJSON[f]["storeNumber"]))["availability"]
					if stockJSON[checkProduct[p]] and storeJSON[f]["storeNumber"] not in alreadyAvailable[checkProduct[p]]: 
						availableStore.append(storeJSON[f]["storeName"])
						alreadyAvailable[checkProduct[p]].append(storeJSON[f]["storeNumber"])
				except: pass
			if len(availableStore)!= 0: 
				singleAdd = "【" + stateName + "】" + ", ".join(availableStore)
				singleProductOutput[checkProduct[p]] += singleAdd
		singleProductOutput[checkProduct[p]] = singleProductOutput[checkProduct[p]].replace(stateStore, "】所有零售店")
	for o in range(0, len(checkProduct)):
		if len(singleProductOutput[checkProduct[o]]) > 0:
			productBasename = checkProduct[o][:-4]
			try:
				if savedName[productBasename] == "[获取产品名称出现错误]": 
					del savedName[productBasename]
			except KeyError: 
				print "Fetching product name for output..."; title(productBasename)
			singleTitle = savedName[productBasename].replace(" - ", "-").split("-")[0]
			upb += "New result for " + checkProduct[o] + ",\n" + singleProductOutput[checkProduct[o]] + "\n"
			IFTTT.pushbots(
				"到货零售店: " + singleProductOutput[checkProduct[o]], singleTitle + "新到货", 
				productImage(productBasename), "raw", masterKey)
		else: print "No new stores detected for product " + checkProduct[o]
		singleProductOutput[checkProduct[o]] = ""
	print upb + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n"
	os.system("rm -f " + rpath + "stockR*"); time.sleep(43200)