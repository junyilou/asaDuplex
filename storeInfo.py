import json

with open("Retail/storeInfo.json") as r:
	info = json.loads(r.read())

with open("Retail/storeList.json") as r:
	asto = json.loads(r.read())["countryStateMapping"]

def StoreID(storeid):
	if type(storeid) == int:
		storeid = f"{storeid:0>3d}"
	storeid = storeid.replace("R", "")
	if len(storeid) == 3:
		try:
			return [(storeid, info["name"][storeid])]
		except KeyError:
			return []
	else:
		return []

def StoreName(name):
	stores = list()
	name = name.replace("_", " ")
	for i in info["name"].keys():
		if info["name"][i] == name:
			stores.append((i, name))
	return stores

def StoreNation(emoji):
	if emoji == "TW":
		emoji = "🇹🇼"
	stores = list()
	for i in info["flag"].keys():
		if info["flag"][i] == emoji:
			storename = info["name"][i]
			if storename[:8] != "Store in":
				stores.append((i, storename))
	return stores

def storeInfo(storeid):
	if type(storeid) == int:
		storeid = f"{storeid:0>3d}"
	storeid = storeid.replace("R", "")
	ret = {}
	for t in info.keys():
		if storeid in info[t].keys():
			ret[t] = info[t][storeid]
	return ret

def storeList(storeid):
	if type(storeid) == int:
		storeid = f"{storeid:0>3d}"
	storeid = "R" + storeid.replace("R", "")
	find = {}
	for i in asto:
		for k in i["states"]:
			for m in k["stores"]:
				if m["storeNumber"] == storeid:
					find = m
					find["stateName"] = k["stateName"]
					find = dict(sorted(find.items(), key = lambda k: k[0]))
	return find

def storeOrder():
	stores = list()
	for i in asto:
		for k in i["states"]:
			stores += sorted([m["storeNumber"] for m in k["stores"]])
	return stores