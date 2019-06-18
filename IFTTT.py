import os

def getkey():
	isKey = os.path.isfile(os.path.expanduser('~') + "/key.txt")
	if not isKey:
		print ("Please provide your IFTTT key in ~/key.txt\n" +
		"Location of the txt can be edited in the source code."); exit()
	else: 
		kOpen = open(os.path.expanduser('~') + "/key.txt")
		masterKey = list()
		for line in open(os.path.expanduser('~') + "/key.txt"):
			line = kOpen.readline().replace("\n", "")
			masterKey.append(line)
		kOpen.close()
	return masterKey

def pushbots(value1, value2, value3, trigger, keylist, debugMode):
	for msk in range(0, len(keylist)):
		checkLoc = os.path.expanduser('~') + "/" + keylist[msk]
		os.system("rm -f " + checkLoc + "*")
		while not os.path.isfile(checkLoc):
			script = ("wget -P ~ -t 100 -T 5 --no-check-certificate --post-data 'value1=" + value1 
			+ "&value2=" + value2 + "&value3=" + value3 + "' https://maker.ifttt.com/trigger/"
			+ trigger + "/with/key/" + keylist[msk])
			if debugMode: print "# - IFTTT PUSHBOTDS DEBUG - #\n" + script + "\n"; break
			else: os.system(script)
		os.system("rm -f " + checkLoc + "*")