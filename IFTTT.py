#-*- coding:utf-8 -*-
import os, sys

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
	reload(sys); sys.setdefaultencoding('utf-8')
	if type(keylist) == str: keylist = keylist.split()
	for msk in range(0, len(keylist)):
		checkLoc = os.path.expanduser('~') + "/" + keylist[msk]
		os.system("rm -f " + checkLoc + "*")
		while not os.path.isfile(checkLoc):
			if debugMode: 
				print "\n### - IFTTT PUSHBOTDS DEBUG - ###\n"
				print "value1: " + value1
				print "value2: " + value2
				print "value3: " + value3
				print "trigger: " + trigger
				print "key: " + keylist[msk], keylist
				print "\n### - IFTTT PUSHBOTDS DEBUG - ###\n"; break
			else: 
				os.system("wget -P ~ -t 100 -T 5 --no-check-certificate --post-data 'value1=" + value1 
				+ "&value2=" + value2 + "&value3=" + value3 + "' https://maker.ifttt.com/trigger/"
				+ trigger + "/with/key/" + keylist[msk])
		os.system("rm -f " + checkLoc + "*")