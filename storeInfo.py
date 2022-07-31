import re
import json
import asyncio
import aiohttp
import logging
from functools import partial

from modules.util import request
from modules.constants import userAgent, webNation, localeNation, RecruitDict

with open("storeInfo.json") as r:
	infoJSON = json.loads(r.read())

LIBRARY = {}
Order = []

def StoreID(sid, fuzzy = False, include_coeff = False):
	stores = []
	if fuzzy:
		sid = f"{sid}".upper().replace("R", "")
		ids = [i for i in LIBRARY]
		for i in ids:
			if sid in i:
				coeff = (round(len(sid) / 3, 3), ) if include_coeff else ()
				stores.append((i, actualName(infoJSON["name"][i]), *coeff))
	else:
		sid = f"{sid:0>3}".upper().replace("R", "")
		if sid in LIBRARY:
			coeff = (1.0, ) if include_coeff else ()
			stores = [(sid, actualName(infoJSON["name"][sid]), *coeff)]
	return stores

def StoreMatch(keyword, fuzzy = False, include_coeff = False):
	stores = []
	keyword = keyword.lower()
	for i in LIBRARY:
		for j in LIBRARY[i]:
			k = j.lower()
			if fuzzy:
				if keyword in k:
					coeff = (round(len(keyword) / len(k), 3), ) if include_coeff else ()
					stores.append((i, actualName(infoJSON["name"][i]), *coeff))
					break
			else:
				if keyword == k:
					coeff = (1.0, ) if include_coeff else ()
					stores.append((i, actualName(infoJSON["name"][i])), *coeff)
					break
	return stores

def actualName(name):
	return name if type(name) == str else name[0]

def storeInfo(sid):
	sid = f"{sid}"
	try:
		sid = StoreID(sid)[0][0]
		return dict([(t, infoJSON[t][sid]) for t in infoJSON if (sid in infoJSON[t]) and (type(infoJSON[t]) == dict)])
	except IndexError:
		return {}

def storeURL(sid = None, sif = None, mode = None):
	if sid:
		sif = storeInfo(sid)
	elif sif:
		pass
	else:
		raise ValueError("Expect either `Store ID` or `sif dictionary` provided")
	try:
		website = sif["key"]["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		if mode == "slug":
			return website
		else:
			return f"https://www.apple.com{webNation[sif['flag']]}/retail/{website}"
	except KeyError:
		return None

async def storeDict(sid = None, sif = None, session = None, mode = "dict"):
	if sid:
		sif = storeInfo(sid)
	elif sif:
		pass
	else:
		raise ValueError("Expect either `Store ID` or `sif dictionary` provided")
	try:
		website = sif["key"]["website"]
		if website == "-":
			website = actualName(sif["name"]).lower().replace(" ", "")
		url = f"https://www.apple.com/rsp-web/store-detail?storeSlug={website}&locale={localeNation[sif['flag']]}&sc=false"
		if mode == "url":
			return url

		r = await request(session = session, url = url, ident = None, 
			headers = userAgent, ensureAns = False, retryNum = 3, timeout = 5)
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

def getNation(sid, userLang = None):
	state = infoJSON["flag"][f"{sid}"]
	if userLang != None:
		name = RecruitDict[state]["name"] if userLang else RecruitDict[state]["altername"][0]
	else:
		name = state
	return name, [i[0] for i in storeReturn(state, remove_closed = True, remove_future = True)]

def stateReplace(rstores, bold = False, number = True, userLang = None):
	stores = rstores.copy()
	if not stores:
		return stores
	while True:
		for store in stores:
			flag = False
			if not store.isdigit():
				continue
			
			nationName, nationStore = getNation(store, userLang = userLang)
			if all([i in stores for i in nationStore]):
				flag = True
				deco = "*" if bold else ""
				stores[stores.index(store)] = f"{deco}{nationName}{deco}" + (f" ({len(nationStore)})" if number else "")
				_ = [stores.remove(j) for j in nationStore if j != store]
			
			stateName, stateStore = getState(store)
			if all([i in stores for i in stateStore]):
				stateLen = len(stateStore)
				if stateLen != 1:
					flag = True
					deco = "*" if bold else ""
					stores[stores.index(store)] = f"{deco}{stateName}{deco}" + (f" ({len(stateStore)})" if number else "")
					_ = [stores.remove(j) for j in stateStore if j != store]
			if flag:
				break
		if flag == False:
			break
	return stores

def storeReturn(args, sort = True, sort_coeff = False, 
	remove_closed = False, remove_future = False, 
	fuzzy = False, needSplit = False):

	ans = []
	if needSplit:
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
		stores = (StoreID(a, fuzzy, sort_coeff) + StoreMatch(a, fuzzy, sort_coeff)) if digit else StoreMatch(a, fuzzy, sort_coeff)
		for s in stores:
			if s and s not in ans:
				sState = getState(s[0], stateOnly = True)
				judge = (remove_future, remove_closed)
				if any(judge):
					if sState == "Internal":
						continue
					if judge[0] and "Store in" in infoJSON["name"][s[0]]:
						continue
					if judge[1] and sState == "Closed":
						continue
				ans.append(s)

	if sort_coeff:
		ans = [i[:2] for i in sorted(ans, key = lambda k: k[2], reverse = True)]

	elif sort:
		order = {}
		for store in ans:
			sid = store[0]
			try:
				order[sid] = Order.index(sid)
			except ValueError:
				order[sid] = 900 + int(sid)
		ans.sort(key = lambda k: order[k[0]])

	return ans

def dieterURL(sid, mode = 0):
	digest = "crop=1" # "output-format=png"
	'''
		Akamai Image Server Refrence: 
		https://developer.goacoustic.com/acoustic-content/docs/how-to-optimize-and-transform-your-images-automatically-with-akamai-1
	'''
	return f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{sid:0>3}.png?{digest}"

async def DieterHeader(rtl, session = None):
	sid = StoreID(rtl)
	sid = sid[0][0] if sid != [] else rtl
	try:
		r = await request(session = session, url = dieterURL(sid), headers = userAgent, ssl = False,
			method = "HEAD", allow_redirects = False, raise_for_status = True, mode = "head", retryNum = 3, timeout = 5)
		return r['Last-Modified'][5:-4]
	except:
		return None

def library():
	global LIBRARY, Order
	LIBRARY = {}
	for i in infoJSON["name"]:
		comp = [infoJSON["name"][i]] if type(infoJSON["name"][i]) == str else infoJSON["name"][i].copy()
		LIBRARY[i] = comp.copy()
		for j in comp:
			if " " in j:
				LIBRARY[i].append(j.replace(" ", ""))
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
				keys += [infoJSON["key"][i][j], infoJSON["key"][i][j].replace(" ", "")]
		LIBRARY[i] = LIBRARY.get(i, []) + keys
	for i in infoJSON["flag"]:
		flag = infoJSON["flag"][i]
		LIBRARY[i] = LIBRARY.get(i, []) + [flag]
		LIBRARY[i] += [RecruitDict[flag]["name"]]
		LIBRARY[i] += RecruitDict[flag]["altername"]
	Order = sorted([i for i in infoJSON["key"]], key = lambda k: f"{storeInfo(k)['flag']} {getState(k, stateOnly = True)}")

library()
def reloadJSON(filename = "storeInfo.json"):
	global infoJSON
	with open(filename) as r:
		infoJSON = json.loads(r.read())
	library()
	return infoJSON["update"]