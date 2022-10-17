import json
import logging
import asyncio
from modules.util import request, session_func
from modules.constants import userAgent
from bs4 import BeautifulSoup

class Band: 

	name: str
	partNumber: str #MGGX3CH/A
	collection: str #hermes
	material: str #nylon
	colorGroup: str #red
	specialEdition: str #special
	newFilter: str #new
	price: float #799.0
	image: str #MGGX3ref
	rootPath: str #apple.com.cn

	bandSize: str #medium
	bandCaseSize: str #49mm
	bandColor: str #starlight
	bandSizeLocalized: str #中号
	bandCaseSizeLocalized: str #49 毫米
	bandColorLocalized: str #星光色

	detailProperty = ["bandSize", "bandCaseSize", "bandColor"]
	dictProperty = ["name", "partNumber", "material", "colorGroup", "specialEdition", "price", "image"] + \
		detailProperty + [(i + "Localized") for i in detailProperty]

	def __init__(self, **kwargs):
		_ = [setattr(self, k, kwargs[k]) for k in kwargs]

	def __repr__(self):
		basic = [self.partNumber, self.name]
		detail = [getattr(self, d) for d in self.detailProperty] if self.isChecked else []
		return ", ".join(basic + detail)

	@property
	def isChecked(self):
		return all([hasattr(self, i) for i in self.detailProperty])

	@property
	def url(self):
		return self.rootPath + "/shop/product/" + self.partNumber

	@property
	def dict(self):
		return {i: getattr(self, i, None) for i in self.dictProperty}

def commonWords(nameList):
	words = []
	for i in nameList:
		for j in list(i):
			if (not j.isalnum()) or (not j.isascii()):
				i = i.replace(j, f"${j}$")
		words.append([strip for k in i.split("$") if (strip := k.strip("- ")) != ""])

	common = words[0]
	for word in words[1:]:
		for w in common.copy():
			if w not in word:
				common.remove(w)
	return "".join(common).lower()

async def getGrids(rootPath, session, semaphore):
	grids = []
	async with semaphore:
		r = await request(session, rootPath + "/shop/watch/bands", headers = userAgent)
	h = BeautifulSoup(r, features = "lxml")

	def get_value(element):
		return None if element is None else element["value"]

	for l in h.find_all("script"):
		if l.string == None or "window.sectionData.push" not in l.string:
			continue

		bands = {}
		r = "]".join(l.string.split("products: ")[1].split("]")[:-1]) + "]"
		for w in json.loads(r):
			band = Band(
				name = w["name"].replace("\u00A0", " "),
				partNumber = w["partNumber"], 
				collection = get_value(w["dimensionValues"]["dimensionCollection"]),
				material = get_value(w["dimensionValues"]["dimensionMaterial"]),
				colorGroup = get_value(w["dimensionValues"]["dimensionBandColor"]),
				specialEdition = get_value(w["dimensionValues"]["dimensionSpecialEdition"]),
				newFilter = get_value(w["dimensionValues"]["dimensionnewfilter"]),
				price = w["currentAmount"],
				image = w["image"]["imageName"],
				rootPath = rootPath
			)
			bands[band.partNumber] = band
		grids.append(bands)

	return grids

async def getBands(bands, session, semaphore):
	collections = {}

	for part in bands:
		band = bands[part]
		if band.isChecked:
			continue
		async with semaphore:
			r = await request(session, band.url, headers = userAgent)
		l = r.split('window.pageLevelData.PDPContent')[1].split("window.pageLevelData.Overview")[0]
		l = json.loads(";".join(l.split(";")[:-1]).lstrip("= "))

		radioValue = {}
		d = l["productVariationsData"]["items"]
		for w in d:
			dimensionGroup = w["value"]["groupKey"]
			radioValue[dimensionGroup] = radioValue.get(dimensionGroup, {})
			for v in w["value"]["variants"]["items"]:
				radioValue[dimensionGroup][v["value"]["radioValue"]] = v["value"]["text"]

		varientPrice = {}
		d = l["variantPrices"]["items"]
		for w in d:
			varientPrice[w["value"]["partNumber"]] = float(w["value"]["price"]["currentPrice"]["raw_amount"])

		variations = []
		v = json.loads(l["productVariationsPart"])["productVariations"]
		for w in v:
			varient = Band(
				name = v[w]["productTitle"].replace("\u00A0", " "),
				partNumber = w, collection = band.collection, 
				material = band.material, colorGroup = None,
				specialEdition = None, image = None, 
				rootPath = band.rootPath, bandSize = v[w]["dimensionbandsize"]
			) if w not in bands else bands[w]

			varient.price = varientPrice.get(varient.partNumber, None)
			varient.bandSize = v[w]["dimensionbandsize"]
			varient.bandCaseSize = v[w]["dimensionCaseSize"]
			varient.bandColor = v[w]["dimensionColor"]
			varient.bandSizeLocalized = radioValue["dimensionbandsize"].get(v[w]["dimensionbandsize"], None)
			varient.bandCaseSizeLocalized = radioValue["dimensionCaseSize"].get(v[w]["dimensionCaseSize"], None)
			varient.bandColorLocalized = radioValue["dimensionColor"].get(v[w]["dimensionColor"], None)
			variations.append(varient.dict)
		variationName = commonWords([v["name"] for v in variations])
		while variationName in collections:
			variationName += "-"
		collections[variationName] = sorted(variations, key = lambda k: k["name"])

	return collections

@session_func
async def main(session):
	semaphore = asyncio.Semaphore(10)
	rootPath = "https://www.apple.com"
	grids = await getGrids(rootPath, session, semaphore)
	tasks = [getBands(grid, session, semaphore) for grid in grids]
	collections = await asyncio.gather(*tasks)
	with open("allBands.json", "w") as w:
		w.write(json.dumps(collections, ensure_ascii = False, indent = 2))

asyncio.run(main())