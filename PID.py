import os, json, time, logging, IFTTT

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'w', datefmt = '%F %T %p')

def checkPID(pid):
	try: os.kill(pid, 0)
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
	except: pass
	else: updtFile(json.dumps(cList))

def addCurrent(fname, fnum): 
	remCurrent(fname)
	oList = openFile()
	oList.update({fname: fnum})
	updtFile(json.dumps(oList))

if __name__ == "__main__":
	cList = openFile()
	if not len(cList): exit()
	for key, value in cList.items():
		if not checkPID(value):
			print("PID " + str(value) + " [" + key + "] exit.")
			IFTTT.pushbots(
				"监测到 PID " + str(value) + " 对应的 " + key + " 已停止工作",
				"Python 3 运行时错误", "", "raw", IFTTT.getkey()[0], 0)
			remCurrent(key)
	logging.info("This is the last time when this script ran.")