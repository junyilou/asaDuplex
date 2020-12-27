import json
import logging

with open("Retail/storeInfo.json") as r:
	j = json.loads(r.read())

def StoreID(storeid):
	if type(storeid) == int:
		storeid = "%03d" % storeid
	storeid = storeid.replace("R", "")
	if len(storeid) == 3:
		try:
			return [(storeid, j["name"][storeid])]
		except KeyError:
			return []
	else:
		return []

def StoreName(name):
	flag = 1
	name = name.replace("_", " ")
	for i in j["name"].keys():
		if j["name"][i] == name:
			return [(i, name)]
	return []

def StoreNation(emoji):
	stores = list()
	for i in j["flag"].keys():
		if j["flag"][i] == emoji:
			storename = j["name"][i]
			if storename[:8] != "Store in":
				stores.append((i, storename))
	return stores