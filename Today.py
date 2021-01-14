import os, json, time, logging, requests
import telegram
requests.packages.urllib3.disable_warnings()

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

filename = ['qibao', 'shanghaiiapm', 'wujiaochang', 'nanjingeast', 'pudong', 'globalharbor','hongkongplaza', 'kunming', 
'sanlitun', 'chinacentralmall', 'chaoyangjoycity', 'wangfujing', 'xidanjoycity', 'mixcchengdu', 'taikoolichengdu', 'tianjinjoycity','riverside66tianjin',
'mixctianjin', 'parc66jinan', 'mixcqingdao', 'parccentral','zhujiangnewtown', 'holidayplazashenzhen', 'mixcnanning', 'nanjingist', 'xuanwulake', 
'wondercity', 'center66wuxi', 'suzhou', 'mixczhengzhou', 'tianyisquare', 'mixchangzhou', 'westlake', 'xiamenlifestylecenter', 'tahoeplaza', 
'olympia66dalian', 'parkland', 'zhongjiejoycity', 'mixcshenyang', 'jiefangbei', 'mixcchongqing', 'paradisewalkchongqing',
'ifcmall', 'festivalwalk', 'cantonroad', 'newtownplaza', 'apmhongkong', 'causewaybay', 'galaxymacau', 'cotaistrip', 'xinyia13', 'taipei101']

storename = ['七宝', '上海环贸 iapm', '五角场', '南京东路', '浦东', '环球港', '香港广场', '昆明', 
'三里屯', '华贸购物中心', '朝阳大悦城', '王府井', '西单大悦城', '成都万象城', '成都太古里', '天津大悦城', '天津恒隆广场', 
'天津万象城', '济南恒隆广场', '青岛万象城', '天环广场', '珠江新城', '深圳益田假日广场', '南宁万象城', '南京艾尚天地', '玄武湖', 
'虹悦城', '无锡恒隆广场', '苏州', '郑州万象城', '天一广场', '杭州万象城', '西湖', '厦门新生活广场', '泰禾广场', 
'大连恒隆广场', '百年城', '中街大悦城', '沈阳万象城', '解放碑', '重庆万象城', '重庆北城天街',
'ifc mall', 'Festival Walk', 'Canton Road', 'New Town Plaza', 'apm Hong Kong', 'Causeway Bay', '澳門銀河', '路氹金光大道', '信義 A13', '台北 101']

reg = {"qibao": "cn", "ifcmall": "hk", "galaxymacau": "mo", "xinyia13": "tw"}

appn = ""
with open("Retail/savedEvent.txt") as m: 
	mark = m.read()

if os.path.isdir('logs'):
	logging.basicConfig(
		filename = "logs/" + os.path.basename(__file__) + ".log",
		format = '[%(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, filemode = 'a', datefmt = '%F %T')
else:
	logging.basicConfig(
		format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
		level = logging.INFO, datefmt = '%T')
logging.info("程序启动")

masterJSON = {}
for fn in filename:
	try: region = reg[fn]
	except KeyError: pass

	try:
		logging.info("正在下载活动安排表文件: " + fn)
		r = requests.get("https://www.apple.com/today-bff/landing/store?stageRootPath=/" + region + "&storeSlug=" + fn, verify = False)
		masterJSON[fn] = json.loads(r.text.replace("\u2060", ""))["courses"]
	except: pass

for f in masterJSON:
	fStore = masterJSON[f]
	for fID in fStore:
		fCourse = fStore[fID]
		fName = fCourse["name"].replace("\n", "")
		if (not fName in mark) and (not fName in appn):
			logging.info("在 " + f + " 找到新活动 " + fName)
			appn += fName + ",\n"; stores = storename[filename.index(f)]
			for j in masterJSON:
				jStore = masterJSON[j]
				if jStore == fStore:
					continue
				for jID in jStore:
					jCourse = jStore[jID]
					if (jCourse["name"].replace("\n", "") == fName):
						logging.info("在 " + j + " 找到相同新活动")
						stores += "、" + storename[filename.index(j)]
						break
			push = "#TodayatApple " + fName + "\n@ " + stores + "\n\n" + fCourse["mediumDescription"]
			push = push.replace('"', "").replace("'", "").replace("：", " - ").replace("_", "\_")
			logging.info("输出: " + push.replace("\n", " "))
			photoURL = fCourse["backgroundMedia"]["images"][0]["landscape"]["source"]
			photoURL += "?output-format=jpg&output-quality=80&resize=2880:*"

			logging.getLogger().setLevel(logging.DEBUG)
			bot = telegram.Bot(token = token)
			try:
				bot.send_photo(
					chat_id = chat_id, 
					photo = photoURL,
					caption = '*来自 Today 的通知*\n' + push,
					parse_mode = 'Markdown')
			except:
				logging.error("未能成功发送带有图片的消息")
				bot.send_message(
					chat_id = chat_id,
					text = '*来自 Today 的通知*\n' + push + "\n\n" + photoURL.replace("_", "\_"),
					parse_mode = 'Markdown')
			logging.getLogger().setLevel(logging.INFO)

if appn != "":
	logging.info("正在更新 savedEvent 文件")
	with open("Retail/savedEvent.txt", "w") as m:
		m.write(mark + appn)

logging.info("程序结束")