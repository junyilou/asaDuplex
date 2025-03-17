from itertools import groupby
from math import asin, cos, radians, sin, sqrt
from random import choice

from storeInfo import Store


def haversine(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
	lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
	dlon, dlat = lon2 - lon1, lat2 - lat1
	a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
	c = 2 * asin(sqrt(a))
	return c * 6371

def get_dominating_set[T](G: dict[T, list[T]], start_with: T) -> set[T]:
	# Ref: https://networkx.org/documentation/stable/_modules/networkx/algorithms/dominating.html#dominating_set
	all_nodes = set()
	for v, e in G.items():
		all_nodes.add(v)
		all_nodes.update(e)
	dominating_set = {start_with}
	dominated_nodes = set(G[start_with])
	remaining_nodes = all_nodes - dominated_nodes - dominating_set
	while remaining_nodes:
		v = remaining_nodes.pop()
		undominated_nbrs = set(G.get(v, ())) - dominating_set
		dominating_set.add(v)
		dominated_nodes |= undominated_nbrs
		remaining_nodes -= undominated_nbrs
	return dominating_set

type longitude = float
type latitude = float

def calculate(stores: list[Store], geo_table: dict[str, tuple[longitude, latitude]],
	coverage: int = 12, max_distance: float = 1000) -> dict[str, list[str]]:
	results = {}
	geo = {flag: {i.rid: geo_table[i.rid] for i in grouped}
		for flag, grouped in groupby(sorted(stores), key = lambda i: i.flag)}
	for country in geo.values():
		dst = {sid1: {sid2: haversine(*country[sid1], *country[sid2]) for sid2 in country} for sid1 in country}
		graph = {s: [j for j, d in sorted(dst[s].items(), key = lambda d: d[1])[:coverage]
			if j != s and d <= max_distance] for s in country}
		sets = [get_dominating_set(graph, store) for store in graph]
		answer = choice([s for s in sets if len(s) == min(len(s) for s in sets)])
		results.update({a: graph[a] for a in answer})
	return results