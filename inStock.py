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

checkProduct = sys.argv[1:]; combProduct = ",".join(checkProduct); 
alreadyAvailable = {}; singleProductOutput = {}; upb = ""; global savedName; savedName = {}
statesJSON = json.loads(fileOpen(rpath + "storeList.json"))["countryStateMapping"][0]["states"]
for j in range(len(checkProduct)): alreadyAvailable[checkProduct[j]] = []; singleProductOutput[checkProduct[j]] = ""

while True:
	stateStore = ""
	for s in range(len(statesJSON)):
		stateName = statesJSON[s]["stateName"]; storeJSON = statesJSON[s]["stores"]; stateStore += "【" + stateName + "】"
		for t in range(len(storeJSON)):
			passCheck = 0; stateStore += storeJSON[t]["storeName"] + ", "
			for c in range(len(checkProduct)): 
				if storeJSON[t]["storeNumber"] in alreadyAvailable[checkProduct[c]]: passCheck += 1
			if passCheck == len(checkProduct): continue
			dLoc = rpath + "stock" + storeJSON[t]["storeNumber"]
			os.system("wget -t 100 -T 5 -q -O " + dLoc + " --header 'x-ma-pcmh: REL-" + asaVersion + 
				"' --header 'X-DeviceConfiguration: ss=2.00;vv=5.4.1;sv=12.3.1' " + 
				"'https://mobileapp.apple.com/mnr/p/cn/rci/rciCheckForPart?partNumber=" +
				combProduct + "&storeNumber=" + storeJSON[t]["storeNumber"] + "'")
			print "[" + str(s + 1) + "/" + str(len(statesJSON)) + "] Download in Progress: " + str((t + 1) * 100 / len(storeJSON)) + "%\r",
			sys.stdout.flush()
		stateStore = stateStore[:-2]; print
		for p in checkProduct:
			availableStore = []
			for f in storeJSON:
				try:
					stockJSON = json.loads(fileOpen(rpath + "stock" + f["storeNumber"]))["availability"]
					if stockJSON[p] and f["storeNumber"] not in alreadyAvailable[p]: 
						availableStore.append(f["storeName"])
						alreadyAvailable[p].append(f["storeNumber"])
				except: pass
			if len(availableStore): 
				singleAdd = "【" + stateName + "】" + ", ".join(availableStore)
				singleProductOutput[p] += singleAdd
	singleProductOutput[p] = singleProductOutput[p].replace(stateStore, "all across Mainland China")
	for o in checkProduct:
		if len(singleProductOutput[o]) > 0:
			productBasename = o[:-4]
			try:
				if savedName[productBasename] == "[获取产品名称出现错误]": 
					del savedName[productBasename]
			except KeyError: 
				print "Fetching product name for output..."; title(productBasename)
			singleTitle = savedName[productBasename].replace(" - ", "-").replace("USB-C", "USB C").split("-")[0]
			upb += "New result for " + o + ",\n" + singleProductOutput[o] + "\n"
			pushOut = "到货零售店: " + singleProductOutput[o]
			pushOut = pushOut.replace("到货零售店: all across Mainland China", "全中国大陆 Apple Store 零售店均已到货该产品")
			IFTTT.pushbots(
				pushOut, singleTitle + "新到货", 
				productImage(productBasename), "raw", masterKey, 0)
		else: print "No new stores detected for product " + o
		singleProductOutput[o] = ""
	print upb + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n"
	os.system("rm -f " + rpath + "stockR*"); time.sleep(43200)