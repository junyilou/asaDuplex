#-*- coding:utf-8 -*-
import urllib2, os, sys, time, ssl, IFTTT, PID
from BeautifulSoup import BeautifulSoup

alphabet = [chr(i) for i in range(65, 90)]
removeList = ['B', 'I', 'O', 'S']
alphabet = [t for t in alphabet if t not in removeList]
numlist = [chr(i) for i in range(48, 58)]
flist = numlist + alphabet
psbhd = ['V', 'W']
ans = list()

def title(partno):
	reload(sys); sys.setdefaultencoding('utf-8')
	url = "https://www.apple.com/cn/shop/product/" + partno
	try: soup = BeautifulSoup(urllib2.urlopen(url, timeout = 20))
	except: return "[获取产品名称出现错误]"
	else: return soup.title.string.replace(" - Apple (中国大陆)", "").replace(" - Apple", "").replace("购买 ", "")

def productImage(partno):
	return ("https://as-images.apple.com/is/image/AppleInc/aos/published/images" 
		+ partno[0] + partno[:2] + "/" + partno + "/" + partno + "?fmt=png")

for k in range(len(psbhd)):
	for i in range(len(flist)):
		for j in range(len(flist)):
			slct = psbhd[k] + flist[i] + flist[j]
			ans.append('M' + slct + '2')

mOpen = open(os.path.expanduser('~') + "/savedProduct.txt")
mRead = mOpen.read(); mOpen.close(); mSplit = mRead.split(", ")
for r in range(len(mSplit)): 
	mSplit[r] = mSplit[r].replace("\n", "")
	try: ans.remove(mSplit[r])
	except ValueError: pass
masterKey = IFTTT.getkey()
PID.addCurrent(os.path.basename(__file__), os.getpid())

runtim, upb = 0, ""
while True:
	setans = sys.argv[1:]
	if len(setans) != 0: ans = sys.argv[1:]
	runtim += 1; runnot = "[" + str(runtim) + "] "; outPlus = ""
	newList = list(); newTitle = list(); rmList = list()
	for a in range(len(ans)):
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
			if len(setans) == 0: print uOut; upb += uOut; outPlus += ", " + ans[a]
		if len(setans) != 0 and len(newList) > 0: print setans[a], title(setans[a])
		elif a + 1 == len(ans) or ans[a][2] != ans[a + 1][2]:
			if len(newList) < 4:
				for e in range(len(newList)):
					IFTTT.pushbots(
						"Apple Online Store 更新了新产品：" + title(newList[e]) + "，产品部件号：" + newList[e] + "。", 
						productImage(newList[e]), url.replace(ans[a], newList[e]), "linkraw", masterKey[0], 0)
			else:
				for nt in range(len(newList)): 
					print "Fetching product name for output... [" + str(nt + 1) + "/" + str(len(newList)) + "]\r",
					sys.stdout.flush(); newTitle.append("[" + newList[nt] + "] " + title(newList[nt]))
				IFTTT.pushbots(
					"".join(newTitle), "Apple Online Store 更新了多个商品", 
					productImage(newList[0]), "raw", masterKey[0], 0)
			newList = list(); newTitle = list()
	if len(setans) != 0: exit()
	if outPlus != "":
		mOpen = open(os.path.expanduser('~') + "/savedProduct.txt")
		mRead = mOpen.read(); mOpen.close(); mSort = mRead + outPlus
		mSort = mSort.split(", "); mSort.sort(); mSort = ", ".join(mSort)
		mWrite = open(os.path.expanduser('~') + "/savedProduct.txt", "w")
		mWrite.write(mSort); mWrite.close()
	if len(setans) == 0: print "\n" + upb + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "\n"
	for rm in range(len(rmList)): ans.remove(rmList[rm])
	rmList = list(); time.sleep(43200)