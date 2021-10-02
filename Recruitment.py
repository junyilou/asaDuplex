import os
import json
import time
import logging
import requests
requests.packages.urllib3.disable_warnings()

from sdk_aliyun import post
from modules.constants import RecruitDict, disMarkdown, setLogger, userAgent
from bot import chat_ids

from sys import argv
if len(argv) > 1 and argv[1] == "special":
	RecruitDict = {
		"🇦🇪": {"name": "阿联酋", "code": 8225}, 
		"🇨🇳": {"name": "中国", "code": 8030}
	}

wAns = ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop@2x.jpg"

with open("Retail/savedJobs.txt") as m: mark = m.read()

setLogger(logging.INFO, os.path.basename(__file__))
logging.info("程序启动")

s = requests.Session()

for ste in RecruitDict:
	scn = RecruitDict[ste]["name"]
	spl = RecruitDict[ste]["code"]

	realCode = f"11443{spl}"
	logging.info(f"正在下载{scn}的国家文件")

	try:
		r = s.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{realCode}/stateProvinceList", headers = userAgent, verify = False)
	except:
		logging.error(f"下载{scn}的国家文件错误")
		continue
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

		try:
			r = s.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{realCode}/storeLocations?searchField=stateProvince&fieldValue={i['id']}", headers = userAgent, verify = False)
		except:
			logging.error(f"下载{scn}的城市文件 {cID} 错误")
			continue
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
				pushAns = f"#新店新机遇\n\n*{ste} {scn}新增招聘地点*\n{rolloutCode} - {c['name']}\n\n{linkURL}"
				
				push = {
					"mode": "photo-text",
					"text": disMarkdown(pushAns),
					"chat_id": chat_ids[0],
					"parse": "MARK",
					"image": imageURL
				}
				post(push)

if wAns != "":
	logging.info("正在更新 savedJobs 文件")
	with open("Retail/savedJobs.txt", "w") as m:
		m.write(mark + wAns)

logging.info("程序结束")