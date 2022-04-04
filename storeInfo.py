import re
import json
import asyncio
import aiohttp
from functools import partial
from datetime import datetime

from modules.constants import request as request
from modules.constants import userAgent, webNation, localeNation, dieterURL, RecruitDict

with open("storeInfo.json") as r:
	infoJSON = json.loads(r.read())

storeLibrary = {}
Order = []

def StoreID(storeid, fuzzy = False):
	stores = []
	if fuzzy:
		storeid = storeid.upper().replace("R", "")
		ids = [i for i in storeLibrary]
		for i in ids:
			if str(storeid) in i:
				stores.append((i, actualName(infoJSON["name"][i])))
	else:
		i = f"{storeid:0>3}".upper().replace("R", "")
		if i in storeLibrary:
			stores = [(i, actualName(infoJSON["name"][i]))]
	return stores

def StoreMatch(keyword, fuzzy = False):
	stores = []
	keyword = keyword.lower()
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
	storeid = f"{storeid}"
	try:
		sid = StoreID(storeid)[0][0]
		return dict([(t, infoJSON[t][sid]) for t in infoJSON if (sid in infoJSON[t]) and (type(infoJSON[t]) == dict)])
	except IndexError:
		return {}

def storeURL(storeid = None, sif = None):
	if storeid:
		sif = storeInfo(storeid)
	elif sif:
		pass
	else:
		raise ValueError("Expect either `Store ID` or `sif dictionary` provided")
	try:
		website = sif["key"]["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		url = f"https://www.apple.com{webNation[sif['flag']]}/retail/{website}"
		return url
	except KeyError:
		return None

async def storeDict(session, storeid = None, sif = None, mode = "dict"):
	if storeid:
		sif = storeInfo(storeid)
	elif sif:
		pass
	else:
		raise ValueError("Expect either `Store ID` or `sif dictionary` provided")
	try:
		website = sif["key"]["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={website}&locale={localeNation[sif['flag']]}&sc=false"

		r = await request(session = session, url = url, ident = None, headers = userAgent, ensureAns = False)
		r = json.loads(r)

		if mode == "raw":
			return r
		try:
			hours = {
				"isnso": r["hours"]["isNSO"],
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

def getState(sid, stateOnly = False):
	sid = f"{sid}"
	state = infoJSON["key"][sid]["state"]
	if stateOnly:
		return state
	else:
		stores = [i for i in infoJSON["key"] if \
			(infoJSON["key"][i]["state"] == state) and \
			("Store in " not in infoJSON["name"][i])]
		return state, stores

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

def storeReturn(args, sort = True, remove_closed = False, remove_future = False, fuzzy = False, needSplit = False):
	ans = []
	if needSplit: # 一个以空格间隔的词典，或者一个字符串，待以逗号进行拆分
		args = re.split(",|，", "".join(args))
	if type(args) in [int, str]:
		args = [f"{args}"]
	for a in args:
		a = a.strip()
		if not a:
			continue
		if a == "all":
			a = ""
		digit = a.isdigit() or a.upper().replace("R", "").isdigit()
		stores = (StoreID(a, fuzzy) + StoreMatch(a, fuzzy)) if digit else StoreMatch(a, fuzzy)
		for s in stores:
			if s and s not in ans:
				sState = getState(s[0], stateOnly = True)
				judge = (remove_future, remove_closed)
				if any(judge):
					if sState == "公司门店":
						continue
					if judge[0] and "Store in" in infoJSON["name"][s[0]]:
						continue
					if judge[1] and sState == "已关闭":
						continue
				ans.append(s)

	if sort:
		order = {}
		for store in ans:
			sid = store[0]
			try:
				order[sid] = Order.index(sid)
			except ValueError:
				order[sid] = 900 + int(sid)
		ans.sort(key = lambda k: order[k[0]])
	return ans

async def DieterHeader(session, rtl):
	sid = StoreID(rtl)
	sid = sid[0][0] if sid != [] else rtl
	try:
		async with session.head(
			url = dieterURL(sid), headers = userAgent, ssl = False,
			allow_redirects = False, raise_for_status = True) as resp:
			r = resp.headers
		return r['Last-Modified'][5:-4]
	except:
		return None

def library():
	global storeLibrary, Order
	storeLibrary = {}
	for i in infoJSON["name"]:
		comp = [infoJSON["name"][i]] if type(infoJSON["name"][i]) == str else infoJSON["name"][i]
		for j in comp:
			storeLibrary[i] = storeLibrary.get(i, []) + [j]
	for i in infoJSON["key"]:
		keys = []
		for j in infoJSON["key"][i]:
			if j == "website":
				if infoJSON["key"][i][j] == "-":
					keys.append(actualName(infoJSON["name"][i]).lower().replace(" ", ""))
				else:
					keys.append(infoJSON["key"][i][j])
			elif j == "alter":
				keys += infoJSON["key"][i][j].split(" ")
			else:
				keys += [infoJSON["key"][i][j]]
		storeLibrary[i] = storeLibrary.get(i, []) + keys
	for i in infoJSON["flag"]:
		flag = infoJSON["flag"][i]
		storeLibrary[i] = storeLibrary.get(i, []) + [flag]
		storeLibrary[i] += [RecruitDict[flag]["name"]]
		storeLibrary[i] += RecruitDict[flag]["altername"]
	Order = sorted([i for i in infoJSON["key"]], key = lambda k: f"{storeInfo(k)['flag']} {getState(k, stateOnly = True)}")

library()
def reloadJSON(filename = "storeInfo.json"):
	global infoJSON
	with open(filename) as r:
		infoJSON = json.loads(r.read())
	library()
	return infoJSON["update"]