import os, json, time, IFTTT

def checkPID(pid):
	try: os.kill(pid,0)
	except OSError: return False
	else: return True

def openFile(): 
	f = open(os.path.expanduser("~") + "/pid.txt"); g = f.read(); f.close()
	try: h = json.loads(g)
	except ValueError: h = json.loads("{}")
	return h

def updtFile(v): 
	u = open(os.path.expanduser("~") + "/pid.txt", "w"); u.write(v); u.close()

def remCurrent(fname):
	cList = openFile()
	try: cList.pop(fname)
	except KeyError: pass
	else: updtFile(json.dumps(cList))

def addCurrent(fname, fnum): 
	remCurrent(fname); updtFile(json.dumps(dict(openFile().items() + {fname: fnum}.items())))

if __name__ == "__main__":
	while True:
		cList = openFile()
		if not len(cList): exit()
		for key, value in cList.items():
			if not checkPID(value):
				print "PID " + str(value) + " [" + key + "] exit."
				IFTTT.pushbots(
					"Detected PID " + str(value) + ", refrenced to " + key + " exit.",
					"Python Runtime Error", "", "raw", IFTTT.getkey()[0].split(), 0)
				remCurrent(key)
		print time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()); time.sleep(600)