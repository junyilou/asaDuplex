#-*- coding:utf-8 -*-
import urllib2, os, sys, time, ssl, IFTTT
from BeautifulSoup import BeautifulSoup

alphabet = ([chr(i) for i in range(65, 73)] + [chr(i) for i in range(74, 79)] + 
			[chr(i) for i in range(80, 83)] + [chr(i) for i in range(84, 90)]) #I, O, S, Z
numlist = [chr(i) for i in range(48, 58)]
flist = numlist + alphabet
psbhd = ['V', 'W']
global ans; ans = list()

def title(partno):
	reload(sys); sys.setdefaultencoding('utf-8')
	url = "https://www.apple.com/cn/shop/product/" + partno
	try: soup = BeautifulSoup(urllib2.urlopen(url, timeout = 20))
	except: return "[获取产品名称出现错误]"
	else: return soup.title.string.replace(" - Apple (中国大陆)", "").replace(" - Apple", "").replace("购买 ", "")

def productImage(partno):
	return ("https://as-images.apple.com/is/image/AppleInc/aos/published/images" 
		+ partno[0] + partno[:2] + "/" + partno + "/" + partno + "?fmt=png")

for k in range(0, len(psbhd)):
	for i in range(0, len(flist)):
		for j in range(0, len(flist)):
			slct = psbhd[k] + flist[i] + flist[j]
			ans.append('M' + slct + '2')

mOpen = open(os.path.expanduser('~') + "/savedProduct")
mRead = mOpen.read(); mOpen.close(); mSplit = mRead.split(", ")
for r in range(0, len(mSplit)): 
	mSplit[r] = mSplit[r].replace("\n", "")
	try: ans.remove(mSplit[r])
	except ValueError: pass
masterKey = IFTTT.getkey()

def home(setans = list()):
	global runtim, upb, ans
	if len(setans) != 0: ans = setans
	runtim += 1; runnot = "[" + str(runtim) + "] "; outPlus = ""
	newList = list(); newTitle = list(); rmList = list()
	for a in range(0, len(ans)):
		url = 'https://www.apple.com/cn/shop/product/' + ans[a]
		try: p = urllib2.urlopen(url, timeout = 20)
		except ssl.SSLError: 
			print runnot + ans[a] + " 500 [" + str(a + 1) + "/" + str(len(ans)) + "]\r",
			sys.stdout.flush()
		except urllib2.URLError, e:
			if hasattr(e, "code"):
				print runnot + ans[a] + " " + str(e.code) + " [" + str(a + 1) + "/" + str(len(ans)) + "]\r",
				sys.stdout.flush()
			else:
				print runnot + ans[a] + " 400 [" + str(a + 1) + "/" + str(len(ans)) + "]\r",
				sys.stdout.flush()
		else: 
			newList.append(ans[a]); rmList.append(ans[a])
			uOut = "New Product Found: " + ans[a] + " at " + str(a + 1) + "/" + str(len(ans)) + "\n"
			if len(setans) == 0: print uOut; upb += uOut; outPlus += ans[a] + ", "
		if len(setans) != 0 and len(newList) > 0: print setans[a], title(setans[a])
		elif a + 1 == len(ans) or ans[a][2] != ans[a + 1][2]:
			if len(newList) < 4:
				for e in range(0, len(newList)):
					IFTTT.pushbots(
						"Apple Online Store 更新了新产品：" + title(newList[e]) + "，产品部件号：" + newList[e] + "。", 
						productImage(newList[e]), url.replace(ans[a], newList[e]), "linkraw", masterKey[0], 0)
			else:
				for nt in range(0, len(newList)): 
					print "Fetching product name for output... [" + str(nt + 1) + "/" + str(len(newList)) + "]\r",
					sys.stdout.flush(); newTitle.append("[" + newList[nt] + "] " + title(newList[nt]))
				IFTTT.pushbots(
					"".join(newTitle), "Apple Online Store 更新了多个商品", 
					productImage(newList[0]), "raw", masterKey[0], 0)
			newList = list(); newTitle = list()
	if outPlus != "":
		mOpen = open(os.path.expanduser('~') + "/savedProduct")
		mRead = mOpen.read(); mOpen.close()
		mWrite = open(os.path.expanduser('~') + "/savedProduct", "w")
		mWrite.write(mRead + outPlus); mWrite.close()
	if len(setans) == 0: print "\n" + upb + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n"
	for rm in range(0, len(rmList)): ans.remove(rmList[rm])
	rmList = list()

arg = 0; global runtim, upb; runtim = 0; upb = ""
for m in sys.argv[1:]: arg += 1
while True:
	if arg > 0: home(sys.argv[1:]); exit()
	home(); time.sleep(3600)