import os
import json
import logging
import requests
from datetime import datetime
requests.packages.urllib3.disable_warnings()

from sdk_aliyun import post
from modules.constants import RecruitDict, disMarkdown, setLogger, userAgent
from bot import chat_ids

stdout = lambda p: print(datetime.now().strftime("[%F %T] ") + p)
from sys import argv
if len(argv) > 1:
	if "special" in argv:
		RecruitDict = {
			"🇨🇳": {"name": "中国", "code": 114438030}
		}
	if "logging" in argv:
		stdout = logging.info

wAns = ""
imageURL = "https://www.apple.com/jobs/images/retail/hero/desktop@2x.jpg"

with open("Retail/savedJobs.txt") as m: mark = m.read()

setLogger(logging.INFO, os.path.basename(__file__))
stdout("程序启动")

s = requests.Session()

for ste in RecruitDict:
	scn = RecruitDict[ste]["name"]
	spl = RecruitDict[ste]["code"]

	stdout(f"正在下载{scn}的国家文件")

	try:
		r = s.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{spl}/stateProvinceList", headers = userAgent, verify = False)
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

	stdout(f"找到{scn}有城市文件 {len(stateJSON)} 个")
	for i in stateJSON: 
		cID = i["id"].replace("postLocation-", "")
		# stdout(f"正在下载{scn}的城市文件 {cID}")

		try:
			r = s.get(f"https://jobs.apple.com/api/v1/jobDetails/PIPE-{spl}/storeLocations?searchField=stateProvince&fieldValue={i['id']}", headers = userAgent, verify = False)
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
				stdout(f"找到了{scn}的新店 {rolloutCode} 不在已知列表中")

				wAns += f"{ste}{rolloutCode}, "
				linkURL = f"https://jobs.apple.com/zh-cn/details/{spl}"
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
	stdout("正在更新 savedJobs 文件")
	with open("Retail/savedJobs.txt", "w") as m:
		m.write(mark + wAns)

stdout("程序结束")