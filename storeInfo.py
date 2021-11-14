import json
import requests
from functools import partial
from datetime import datetime
requests.packages.urllib3.disable_warnings()

from modules.constants import userAgent, webNation, localeNation, dieterURL, RecruitDict

with open("storeInfo.json") as r:
	infoJSON = json.loads(r.read())
storeLibrary = {}

def StoreID(storeid):
	i = f"{storeid:0>3}".upper().replace("R", "")
	return [(i, actualName(infoJSON["name"][i]))] if i in storeLibrary else []

def StoreMatch(keyword, fuzzy = False):
	stores = []
	keyword = keyword.replace("_", " ").lower()
	for i in storeLibrary:
		if fuzzy:
			if any([keyword in j.lower() for j in storeLibrary[i]]):
				stores.append((i, actualName(infoJSON["name"][i])))
		else:
			if any([keyword == j.lower() for j in storeLibrary[i]]):
				stores.append((i, actualName(infoJSON["name"][i])))
	return stores

def actualName(name):
	return name if type(name) == str else name[0]

def storeInfo(storeid):
	try:
		sid = StoreID(storeid)[0][0]
		return dict([(t, infoJSON[t][sid]) for t in infoJSON if (sid in infoJSON[t]) and (type(infoJSON[t]) == dict)])
	except IndexError:
		return {}

def storeURL(storeid):
	sif = storeInfo(storeid)
	try:
		website = sif["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		url = f"https://www.apple.com{webNation[sif['flag']]}/retail/{website}"
		return url
	except KeyError:
		return None

def storeDict(storeid, mode = "dict"):
	sif = storeInfo(storeid)
	try:
		website = sif["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={website}&locale={localeNation[sif['flag']]}&sc=false"
		
		r = requests.get(url, headers = userAgent).json()
		try:
			hours = {
				"regular": r["hours"]["hoursData"],
				"special": r["hours"]["specialHoursData"]
			}
		except:
			hours = {}
		if mode == "hours":
			return hours
		if mode == "dict":
			add = r["address"]
			address = add["address1"].rstrip(" ")
			address += f', {add["address2"]}' if add["address2"] else ""
			prov = add["city"]
			prov += f', {add["stateName"]}' if add["stateName"] else ""
			prov += f', {add["postal"]}' if add["postal"] else ""

			page = {
				**r["geolocation"],
				"timezone": r["timezone"],
				"telephone": r["telephone"],
				"address": address,
				"province": prov,
				**hours
			}
		return page
	except:
		return {}

def storeState(stateCode):
	states = []
	if stateCode not in infoJSON["state"]:
		return {}
	reply = "\n".join([f"    *{prov} -* " + 
		"、".join([f"{StoreID(store)[0][1]} (R{store})" for store in infoJSON["state"][stateCode][prov]]) \
		for prov in infoJSON["state"][stateCode]])
	return reply

def getState(sid):
	sid = f"{sid}"
	for i in infoJSON["state"]:
		for j in infoJSON["state"][i]:
			if sid in infoJSON["state"][i][j]:
				return j, infoJSON["state"][i][j]

def stateReplace(rstores):
	stores = rstores.copy()
	if not stores:
		return stores
	while True:
		for store in stores:
			flag = False
			if not store.isdigit():
				continue
			stateName, stateStore = getState(store)
			if all([i in stores for i in stateStore]):
				stores[stores.index(store)] = f"{stateName} ({len(stateStore)})"
				[stores.remove(j) for j in stateStore if j != store]
				flag = True
			if flag:
				break
		if flag == False:
			break
	return stores

def storeOrder():
	stores = []
	state = infoJSON["state"]
	for i in state:
		for j in state[i]:
			for k in state[i][j]:
				stores.append(k)
	return stores

def storeReturn(args, sort = True, remove_close = False, remove_future = False, fuzzy = False, no_country = False):
	ans = []
	if type(args) == str:
		args = args.split(" ")
	for a in args:
		digit = a.isdigit() or a.upper().replace("R", "").isdigit()
		stores = (StoreID(a) + StoreMatch(a, fuzzy)) if digit else StoreMatch(a, fuzzy)
		for s in stores:
			if s and s not in ans:
				if remove_close and getState(s[0])[0] == "已关闭":
					continue
				if remove_future and "Store in" in infoJSON["name"][s[0]]:
					continue
				if no_country:
					nmlst = [RecruitDict[i]["name"] for i in RecruitDict]
					if a in nmlst or a in webNation:
						continue
				ans.append(s)

	if sort:
		order = {}
		Order = storeOrder()
		for store in ans:
			sid = store[0]
			try:
				order[sid] = Order.index(sid)
			except ValueError:
				order[sid] = 900 + int(sid)
		ans.sort(key = lambda k: order[k[0]])
	return ans

def DieterInfo(rtl):
	sif = storeInfo(rtl)
	if sif:
		name = actualName(sif["name"])
		info = f"*{sif['flag']} Apple {name}* (R{rtl})"
		if "nso" in sif:
			info += f'\n首次开幕于 {datetime.strptime(sif["nso"], "%Y-%m-%d").strftime("%Y 年 %-m 月 %-d 日")}'
	return info

def DieterHeader(rtl):
	sid = StoreID(rtl)
	if not len(sid):
		return None
	else:
		try:
			r = requests.head(dieterURL(sid[0][0]), headers = userAgent, allow_redirects = True, verify = False, timeout = 5)
		except requests.exceptions.ReadTimeout:
			return None
		if r.status_code in [403, 404, 422, 500, 502]:
			return None
		else:
			return r.headers['Last-Modified'][5:-4]

def library():
	global storeLibrary
	storeLibrary = {}
	for i in infoJSON["name"]:
		comp = [infoJSON["name"][i]] if type(infoJSON["name"][i]) == str else infoJSON["name"][i]
		for j in comp:
			storeLibrary[i] = storeLibrary.get(i, []) + [j]
	for i in infoJSON["state"]:
		for j in infoJSON["state"][i]:
			for s in infoJSON["state"][i][j]:
				storeLibrary[s] = storeLibrary.get(s, []) + [j]
	for i in infoJSON["alias"]:
		for j in infoJSON["alias"][i]:
			storeLibrary[j] = storeLibrary.get(j, []) + [i]
	for i in infoJSON["website"]:
		website = infoJSON["website"][i]
		if website == "-":
			website = actualName(infoJSON["name"][i]).lower().replace(" ", "")
		storeLibrary[i] = storeLibrary.get(i, []) + [website]
	for i in infoJSON["flag"]:
		flag = infoJSON["flag"][i]
		storeLibrary[i] = storeLibrary.get(i, []) + [flag]
		if flag == "🇭🇰":
			storeLibrary[i] = storeLibrary.get(i, []) + ["HK", "Hong Kong"]
		if flag == "🇹🇼":
			storeLibrary[i] = storeLibrary.get(i, []) + ["TW", "Taiwan"]
		storeLibrary[i] += [RecruitDict[flag]["name"]]
		storeLibrary[i] += RecruitDict[flag]["altername"]

library()
def reloadJSON(filename = "storeInfo.json"):
	global infoJSON
	with open(filename) as r:
		infoJSON = json.loads(r.read())
	library()
	return infoJSON["update"]