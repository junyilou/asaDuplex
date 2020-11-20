import os, sys, logging, requests

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.DEBUG, datefmt = '%T')

def getkey():
	isKey = os.path.isfile(os.path.expanduser('~') + "/key.txt")
	if not isKey:
		print("用户目录下未找到 key.txt 文件")
		exit()
	else: 
		with open(os.path.expanduser('~') + "/key.txt") as fin:
			masterKey = [i for i in fin.read().split("\n") if i != ""]
	return masterKey

def pushbots(value1, value2, value3, trigger, keylist, logMode):
	if type(keylist) == str: keylist = keylist.split()

	logging.info("启动 IFTTT 推送，收到的 trigger 是 " + trigger)
	logging.info("参数一 " + value1)
	logging.info("参数二 " + value2)
	logging.info("参数三 " + value3)
	logging.info("Key 列表: " + str(keylist))

	if not logMode:
		for msk in range(0, len(keylist)):
			requests.post(
				"https://maker.ifttt.com/trigger/" + trigger + "/with/key/" + keylist[msk],
				data = {"value1": value1, "value2": value2, "value3": value3})
		logging.info("退出 IFTTT 推送")
	else:
		logging.info("目前是 logMode 状态下，不会进行输出")
