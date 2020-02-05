import urllib.request, urllib.error, os, sys, IFTTT, logging
from bs4 import BeautifulSoup
from socket import timeout

userAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) \
AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Safari/605.1.15"
alphabet = [chr(i) for i in range(65, 90)]
removeList = ['B', 'I', 'O', 'S']
alphabet = [t for t in alphabet if t not in removeList]
numlist = [chr(i) for i in range(48, 58)]
flist = numlist + alphabet
psbhd = ['W', 'X']
ans = list()

logging.basicConfig(
	filename = os.path.expanduser('~') + "/logs/" + os.path.basename(__file__) + ".log",
	format = '[%(asctime)s %(levelname)s] %(message)s',
	level = logging.DEBUG, filemode = 'a', datefmt = '%F %T %p')
logging.info("程序启动")

def title(partno):
	url = "https://www.apple.com.cn/shop/product/" + partno
	req = urllib.request.Request(url, headers = {'User-Agent': userAgent})
	try: 
		soup = BeautifulSoup(urllib.request.urlopen(req, timeout = 20), features = "html.parser")
	except: 
		logging.error("获取产品 " + partno + " 的名称失败")
		return "Apple 产品"
	else: 
		return soup.title.string.replace(" - Apple (中国大陆)", "").replace(" - Apple", "").replace("购买 ", "")

def productImage(partno): 
	return "https://as-images.apple.com/is/" + partno + "?wid=1280"

for k in psbhd:
	for i in flist:
		for j in flist:
			ans.append('M' + k + i + j + '2')

savedProduct = os.path.expanduser('~') + "/savedProduct.txt"
with open(savedProduct) as fin:
	mSplit = fin.read().split(", ")
for r in range(len(mSplit)): 
	mSplit[r] = mSplit[r].replace("\n", "")
	try: ans.remove(mSplit[r])
	except ValueError: pass

amount = len(ans)
logging.info("共计生成 " + str(amount) + " 个产品部件号码")
masterKey = IFTTT.getkey()

setans = sys.argv[1:]
if len(setans) != 0: 
	for a in setans:
		print("[" + a + "] " + title(a))
	logging.info("onlineCrawl 标题模式，程序结束")
	exit()

outPlus = ""; newList = list()
for a in range(amount):
	if a == 0: logging.info("开始枚举产品")
	if a == int(amount / 4): logging.info("已完成 1/4")
	if a == int(amount / 2): logging.info("已完成 1/2")
	if a == int(amount * 3 / 4): logging.info("已完成 3/4")
	print("[DEBUG] Working on [" + str(a) + "] " + ans[a] + "\r", end = "")
	sys.stdout.flush()

	url = 'https://www.apple.com.cn/shop/product/' + ans[a]
	req = urllib.request.Request(url, headers = {'User-Agent': userAgent})
	try: p = urllib.request.urlopen(req, timeout = 20)
	except timeout: 
		logging.error(ans[a] + " 请求超时")
	except urllib.error.URLError as e:
		if hasattr(e, "code") and e.code != 404:
			logging.error(ans[a] + " 返回了 HTTP " + str(e.code) + " 错误")
	else:
		logging.info("找到新产品 " + ans[a])
		newList.append(ans[a]); outPlus += ", " + ans[a]

	if a + 1 == amount or len(newList) > 9:
		if len(newList) < 4:
			logging.info("累计新产品不超过 4 个，准备逐个输出")
			for e in range(len(newList)):
				pushAns = "Apple Online Store 更新了新产品：" + title(newList[e]) + "，产品部件号：" + newList[e] + "。"
				logging.info("[运行结果] " + pushAns)
				IFTTT.pushbots(pushAns, productImage(newList[e]), url.replace(ans[a], newList[e]), "linkraw", masterKey[0], 0)
		else:
			newTitle = list()
			for nt in newList: 
				logging.info("正在获得 " + nt + " 的产品名称用于输出")
				newTitle.append("[" + nt + "] " + title(nt) + " ")
			existProduct = -1
			for imt in range(len(newList)):
				logging.info("正在检查产品图片存在性... [" + str(imt + 1) + "/" + str(len(newList)) + "]")
				try: imo = urllib.request.urlopen(productImage(newList[imt]), timeout = 20)
				except (timeout, urllib.error.URLError): pass
				else: existProduct = imt; break
			if existProduct == -1: outputImage = ""
			else: outputImage = productImage(newList[existProduct])
			logging.info("[运行结果] " + "".join(newTitle))
			IFTTT.pushbots("".join(newTitle), "Apple Online Store 更新了多个商品", outputImage, "raw", masterKey[0], 0)
		newList = list()

if outPlus != "":
	with open(savedProduct) as fin:
		mSort = (fin.read() + outPlus).split(", ")
	mSort.sort(); mSort = ", ".join(mSort)
	with open(savedProduct, "w") as fout:
		fout.write(mSort)
	logging.info("共产生 " + str(outPlus.count(",")) + " 个新产品，已生成新的 savedProduct")

logging.info("程序结束")