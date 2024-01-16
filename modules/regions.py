import json
from dataclasses import dataclass
from typing import Optional

@dataclass(order = True, frozen = True, slots = True)
class Region:
	flag: str
	abbr: str
	job_code: dict[str, int]
	locale: str
	name: str
	name_alter: list[str]
	name_eng: str
	part_sample: Optional[str]
	post_location: str
	url_app: Optional[str]
	url_taa: str
	url_retail: str
	url_store: Optional[str]

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} {self.abbr}: {self.name}>"

with open("regions.json") as r:
	RegionList = [Region(**d) for d in json.load(r)]

Regions = {r.flag: r for r in RegionList}