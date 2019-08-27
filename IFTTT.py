import os, sys

def getkey():
	isKey = os.path.isfile(os.path.expanduser('~') + "/key.txt")
	if not isKey:
		print("请把 IFTTT Maker 的 Query Key 放在 ~/key.txt 中\n" +
		"该文本文档的位置可以通过修改 IFTTT.py 的源代码来调整"); exit()
	else: 
		kOpen = open(os.path.expanduser('~') + "/key.txt")
		masterKey = list()
		for line in open(os.path.expanduser('~') + "/key.txt"):
			line = kOpen.readline().replace("\n", "")
			masterKey.append(line)
		kOpen.close()
	return masterKey

def pushbots(value1, value2, value3, trigger, keylist, debugMode):
	if type(keylist) == str: keylist = keylist.split()
	for msk in range(0, len(keylist)):
		checkLoc = os.path.expanduser('~') + "/" + keylist[msk]
		os.system("rm -f " + checkLoc + "*")
		while not os.path.isfile(checkLoc):
			if debugMode: 
				print("\n### - IFTTT 推送 DEBUG 模式 - ###\n")
				print("value1: " + value1)
				print("value2: " + value2)
				print("value3: " + value3)
				print("trigger: " + trigger)
				print("key: " + keylist[msk], keylist)
				print("\n### - IFTTT 推送 DEBUG 模式 - ###\n"); break
			else: 
				os.system("wget -P ~ -t 100 -T 5 --no-check-certificate --post-data 'value1=" + value1 
				+ "&value2=" + value2 + "&value3=" + value3 + "' https://maker.ifttt.com/trigger/"
				+ trigger + "/with/key/" + keylist[msk])
		os.system("rm -f " + checkLoc + "*")