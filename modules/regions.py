import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(order = True, slots = True, frozen = True)
class Region:
	abbr: str
	apu: bool
	flag: str
	locale: str
	name: str
	name_alt: list[str] = field(hash = False)
	name_eng: str
	part_sample: str | None
	post_location: str
	url_app: str | None
	url_retail: str
	url_store: str | None
	url_taa: str | None

	def __repr__(self) -> str:
		return f"<{self.__class__.__name__} {self.abbr}: {self.name}>"

f = json.loads(Path(__file__).with_suffix(".json").read_text())
RegionList = [Region(**d) for d in f]
Regions = {r.flag: r for r in RegionList}