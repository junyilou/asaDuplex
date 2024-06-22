import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(order = True, slots = True)
class Region:
	abbr: str
	apu: bool
	flag: str
	locale: str
	name: str
	name_alt: list[str]
	name_eng: str
	part_sample: Optional[str]
	post_location: str
	url_app: Optional[str]
	url_retail: str
	url_store: Optional[str]
	url_taa: str

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} {self.abbr}: {self.name}>"

f = json.load(Path(__file__).with_suffix(".json").open())
RegionList = [Region(**d) for d in f]
Regions = {r.flag: r for r in RegionList}