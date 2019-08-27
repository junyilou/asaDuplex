import itertools, json, os
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
	lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
	dlon = lon2 - lon1; dlat = lat2 - lat1
	a = sin(dlat/2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon/2) ** 2
	c = 2 * asin(sqrt(a))
	r = 6370.856
	return c * r

rpath = os.path.expanduser('~') + "/Retail/"
jOpen = open(rpath + "storeList.json"); jRead = json.loads(jOpen.read())
jOpen.close(); countryState = jRead["countryStateMapping"]

outList = list(); singleOut = ""

for country in countryState:
	singleCountry = country["states"]
	for state in singleCountry:
		stateStore = state["stores"]
		if len(stateStore) > 1: 
			stateCoordinates = list()
			for store in stateStore:
				stateCoordinates.append([float(store["longitude"]), float(store["latitude"]), "Apple " + store["storeName"]])
			combo = list(itertools.combinations(stateCoordinates, 2))
			distanceList = list()
			for com in combo: 
				distanceList.append((haversine(com[0][0], com[0][1], com[1][0], com[1][1]), com[0][2] + " 到 " + com[1][2] + " 的距离为 "))
			for i in sorted(distanceList, key = lambda distance: distance[0]):
				if i[0] < 3: outList.append((i[0], i[1]))

for j in sorted(outList, key = lambda short: short[0]): 
	if j[0] >= 1: singleOut += j[1] + str(round(j[0], 2)) + " km.\n"
	else: singleOut += j[1] + str(round(j[0] * 1000, 2)) + " m.\n"

ansWrite = open(rpath + "storeAns.txt", "w")
ansWrite.write(singleOut); ansWrite.close()
