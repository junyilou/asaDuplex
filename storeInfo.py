import json, requests
from time import strftime, strptime
requests.packages.urllib3.disable_warnings()

from constants import (
	userAgent, webNation
)

with open("storeInfo.json") as r:
	infoJSON = json.loads(r.read())

def StoreID(storeid):
	if type(storeid) == int or len(storeid) < 3:
		storeid = f"{storeid:0>3}"
	storeid = storeid.upper().replace("R", "")
	if storeid.isdigit():
		try:
			name = actualName(infoJSON["name"][storeid])
			return [(storeid, name)]
		except KeyError:
			return []
	else:
		return []

def StoreName(name):
	stores = []
	name = name.replace("_", " ")
	for i in infoJSON["name"]:
		comp = [infoJSON["name"][i]] if type(infoJSON["name"][i]) == str else infoJSON["name"][i]
		for cname in comp:
			if cname.upper() == name.upper():
				stores.append((i, comp[0]))
	for i in infoJSON["state"]:
		for j in infoJSON["state"][i]:
			if j.upper() == name.upper():
				for s in infoJSON["state"][i][j]:
					stores.append((s, actualName(storeInfo(s)["name"])))
	for i in infoJSON["alias"]:
		if i.upper() == name.upper():
			for s in infoJSON["alias"][i]:
				stores.append((s, actualName(storeInfo(s)["name"])))
	return stores

def StoreNation(emoji):
	if emoji.upper() == "TW":
		emoji = "🇹🇼"
	stores = []
	for i in infoJSON["flag"]:
		if infoJSON["flag"][i] == emoji:
			name = actualName(infoJSON["name"][i])
			if name[:8] != "Store in":
				stores.append((i, name))
	return stores

def actualName(name):
	return name if type(name) == str else name[0]

def storeInfo(storeid):
	sid = StoreID(storeid)[0][0]
	return dict([(t, infoJSON[t][sid]) for t in infoJSON if (sid in infoJSON[t]) and (type(infoJSON[t]) == dict)])

def storeURL(storeid):
	sif = storeInfo(storeid)
	try:
		website = sif["website"]
		name = actualName(sif["name"])
		if website == "-":
			website = name.lower().replace(" ", "")
		url = f"https://www.apple.com{webNation[sif['flag']]}/retail/{website}"
	except KeyError:
		return "N/A"
	return url

def storePage(sid):
	try:
		r = requests.get(storeURL(sid), headers = userAgent).text
	except:
		return ""
	return r

def storeDict(r):
	try:
		j = json.loads(r.split('<script id="__NEXT_DATA__" type="application/json">')[1].split("</script>")[0])
		j = j["props"]["pageProps"]["storeDetailsData"]

		add = j["address"]
		address = add["address1"][:-1] if add["address1"][-1] == " " else add["address1"]
		address += f', {add["address2"]}' if add["address2"] != "" else ""
		prov = add["city"]
		prov += f', {add["stateName"]}' if add["stateName"] != "" else ""
		prov += f', {add["postal"]}' if add["postal"] != "" else ""

		page = {
			**j["geolocation"],
			"timezone": j["timezone"],
			"telephone": j["telephone"],
			"address": address,
			"province": prov
		}
	except:
		return {}
	return page

def storeState(stateCode):
	states = []
	if stateCode not in infoJSON["state"]:
		return {}
	reply = "\n".join([f"    *{prov} -* " + 
		"、".join([f"{StoreID(store)[0][1]} (R{store})" for store in infoJSON["state"][stateCode][prov]]) \
		for prov in infoJSON["state"][stateCode]])
	return reply

def storeOrder():
	stores = []
	state = infoJSON["state"]
	for i in state:
		for j in state[i]:
			for k in state[i][j]:
				stores.append(k)
	return stores

def reloadJSON():
	global infoJSON
	with open("storeInfo.json") as r:
		infoJSON = json.loads(r.read())

def storePairs(args):
	pair = {"r": [], "s": [], "n": []}
	for a in args:
		if a.isdigit() or a.upper().replace("R", "").isdigit():
			pair["r"].append(a)
		elif a in webNation:
			pair["s"].append(a)
		else:
			pair["n"].append(a.replace("Apple_", ""))
	return pair

def storeReturn(pair, accept_function = ['r', 'n', 's'], sort = True):
	stores = list()
	functions = {'r': StoreID, 'n': StoreName, 's': StoreNation}
	for f in accept_function:
		if f in pair:
			S = map(functions[f], pair[f])
			for _s in list(S):
				for __s in _s:
					if __s not in stores:
						stores.append(__s)
	if sort:
		order = {}; Order = storeOrder()
		for store in stores:
			sid = store[0]
			try:
				order[sid] = Order.index(sid)
			except ValueError:
				order[sid] = 900 + int(sid)
		stores.sort(key = lambda k: order[k[0]])
	return stores

def DieterInfo(rtl):
	storeJSON = storeInfo(rtl)
	if "name" in storeJSON:
		name = actualName(storeJSON["name"])
	else:
		name = "Store"
	flag = (storeJSON['flag'] + " ") if "flag" in storeJSON else ""
	nso = (", 首次开幕于 " + strftime("%Y 年 %-m 月 %-d 日", strptime(storeJSON['nso'], "%Y-%m-%d"))) if "nso" in storeJSON else ""
	return f"#图片更新 #标签 {flag}Apple {name}, R{rtl}{nso}"

def DieterHeader(rtl):
	sid = StoreID(rtl)
	if not len(sid):
		return "404"
	else:
		try:
			r = requests.head(f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{sid[0][0]}.png", 
			headers = userAgent, allow_redirects = True, verify = False, timeout = 5)
		except requests.exceptions.ReadTimeout:
			return "404" # Bad Handling Method
		if r.status_code in [403, 404, 500, 502]:
			return "404"
		else:
			return r.headers['Last-Modified'][5:-4]