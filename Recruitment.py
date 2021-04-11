import os, json, time, logging, requests, telegram

from bot import tokens, chat_ids
token = tokens[0]; chat_id = chat_ids[0]

requests.packages.urllib3.disable_warnings()

stateCHN = ["土耳其", "阿联酋", "英国", "德国", "台湾", "美国", 
"墨西哥", "瑞士", "比利时", "荷兰", "西班牙", "香港", "瑞典", "中国", 
"法国", "澳大利亚", "意大利", "澳门", "巴西", "日本", "韩国", "加拿大", "奥地利"]

stateEmoji = ["🇹🇷", "🇦🇪", "🇬🇧", "🇩🇪", "🇹🇼", "🇺🇸", 
"🇲🇽","🇨🇭", "🇧🇪", "🇳🇱", "🇪🇸", "🇭🇰", "🇸🇪", "🇨🇳", 
"🇫🇷", "🇦🇺", "🇮🇹", "🇲🇴", "🇧🇷", "🇯🇵", "🇰🇷", "🇨🇦", "🇦🇹"]

specialistCode = [8164, 8225, 8145, 8043, 8311, 8158, 
8297, 8017, 8251, 8119, 8056, 8082, 8132, 8030, 
8069, 7991, 8095, 8282, 8176, 8106, 8326, 8004, 8333] #JP - Store Leader

from sys import argv
if len(argv) > 1 and argv[1] == "special":
	stateCHN = ["中国"]; stateEmoji = ["🇨🇳"]; specialistCode = [8030]

wAns = ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop@2x.jpg"

userAgent = {
	"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15\
	 (KHTML, like Gecko) Version/14.0.2 Safari/605.1.15"
}

def disMarkdown(text):
	temp = text
	signs = "\\`_{}[]()#+-.!="
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return temp

with open("Retail/savedJobs.txt") as m: mark = m.read()

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

for scn, ste, spl in zip(stateCHN, stateEmoji, specialistCode):
	realCode = f"11443{spl}"
	logging.info(f"正在下载{scn}的国家文件")

	r = requests.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{realCode}/stateProvinceList", headers = userAgent, verify = False)
	try:
		stateJSON = r.json()["searchResults"]
	except:
		if "Maintenance" in r.text:
			logging.error("遇到了 Apple 招聘页面维护")
			break
		else:
			logging.error(f"打开{scn}的国家文件错误")
			continue

	logging.info(f"找到{scn}有城市文件 {len(stateJSON)} 个")
	for i in stateJSON: 
		cID = i["id"].replace("postLocation-", "")
		logging.info(f"正在下载{scn}的城市文件 {cID}")

		r = requests.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{realCode}/storeLocations?searchField=stateProvince&fieldValue={i['id']}", headers = userAgent, verify = False)
		try:
			cityJSON = r.json()
		except:
			if "Maintenance" in r.text:
				break
			else:
				logging.error(f"打开{scn}的城市文件 {cID} 错误")
				continue

		for c in cityJSON:
			rolloutCode = c["code"]
			if not rolloutCode in mark:
				logging.info(f"找到了{scn}的新店 {rolloutCode} 不在已知列表中")

				wAns += f"{ste}{rolloutCode}, "
				linkURL = f"https://jobs.apple.com/zh-cn/details/{realCode}"
				pushAns = f"*来自 Recruitment 的通知*\n{ste}{scn}新增招聘地点\n{rolloutCode} - {c['name']}"
				
				bot = telegram.Bot(token = token)
				bot.send_photo(
					chat_id = chat_id, 
					photo = imageURL,
					caption = disMarkdown(pushAns) + f" [↗]({linkURL})",
					parse_mode = 'MarkdownV2')

if wAns != "":
	logging.info("正在更新 savedJobs 文件")
	with open("Retail/savedJobs.txt", "w") as m:
		m.write(mark + wAns)

logging.info("程序结束")