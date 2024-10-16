import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Self

from modules.regions import Region, RegionList
from modules.util import (SemaphoreType, SessionType, browser_agent,
                          disMarkdown, request, with_semaphore)
from storeInfo import Store, storeReturn

BASE_RULE = r"[BDFGHMNPS][0-9A-Z]{3}[0-9]"
RICH_RULE = r"[0-9A-Z]{5}[A-Z]{1,2}/[A-Z]"
COMP_RULE = r"([BDFGHMNPS][0-9A-Z]{3}[0-9]([A-Z]{1,2}/[A-Z])?)"

@dataclass(order = True, eq = True, slots = True, unsafe_hash = True)
class Product:
	partno: str
	region: Region
	title: Optional[str] = field(default = None, compare = False)
	html: Optional[str] = field(default = None, compare = False, repr = False)
	aos_data: dict[str, dict[str, Any]] = field(default_factory = dict,
		compare = False, repr = False, hash = False)
	status: int = field(default = 404, compare = False, init = False, repr = False)

	DEFAULT_TITLE = "Apple 产品"

	def __post_init__(self) -> None:
		self.partno = re.findall(COMP_RULE, self.partno)[0][0]

	def __repr__(self) -> str:
		return f"<Product {self.region.flag} {self.partno}: {self.title or self.DEFAULT_TITLE}>"

	@staticmethod
	def from_url(url: str) -> "Product":
		URL_RULE = fr"apple.com([\./][^/]*?)/shop/product/{COMP_RULE}"
		host, part, _ = re.findall(URL_RULE, url)[0]
		region = next(i for i in RegionList if i.url_store == host)
		return Product(part, region)

	@property
	def url(self) -> str:
		return f"https://www.apple.com{self.region.url_store}/shop/product/{self.partno}"

	@property
	def base_partno(self) -> str:
		return self.partno[:5]

	@property
	def rich(self) -> bool:
		return bool(re.match(RICH_RULE, self.partno))

	def telename(self, use_base: bool = False) -> str:
		return f"{disMarkdown(self.base_partno if use_base else self.partno, wrap = "*")} "\
			f"{disMarkdown(self.title or "Apple 产品", extra = "*")} [↗]({self.url})"

	async def get_rich_partno(self,
		utilize_html: bool = True,
		session: Optional[SessionType] = None,
		semaphore: Optional[SemaphoreType] = None) -> Optional[str]:
		try:
			async with with_semaphore(semaphore):
				url = self.url.replace(self.partno, self.base_partno)
				r = await request(url, session, "HEAD", headers = browser_agent,
					mode = ["status", "head"], allow_redirects = False)
			self.status = r["status"]
			assert self.status > 200 and self.status < 400
			self.partno = re.findall(RICH_RULE, r["head"]["Location"])[0]
			self.__post_init__()
			return self.partno
		except Exception:
			pass
		try:
			assert utilize_html
			self.html = self.html or await self.get_html(session)
			assert self.html
			r = re.search(fr"{self.base_partno}[A-Z]{{1,2}}/[A-Z]", self.html)
			if r:
				self.partno = r.group()
				self.__post_init__()
				return self.partno
		except Exception:
			pass

	async def get_image_url(self, session: Optional[SessionType] = None) -> Optional[list[str]]:
		from bs4 import BeautifulSoup
		try:
			self.html = self.html or await self.get_html(session)
			assert self.html
			bs = BeautifulSoup(self.html, features = "lxml")
		except:
			return
		try:
			div = bs.find_all("div", "rf-pdp-inline-gallery-thumbnav-item")
			return [d.a.get("href").split("?")[0] for d in div]
		except:
			pass
		try:
			meta: Any = bs.find("meta", property = "og:image")
			content = meta.get("content").split("?")[0]
			return [content]
		except:
			pass

	async def get_title(self, session: Optional[SessionType] = None) -> Optional[tuple[str, Literal["aos", "og"]]]:
		try:
			await self.get_aos_title(ensure = False, session = session)
			assert isinstance(self.title, str)
			return self.title, "aos"
		except:
			pass
		try:
			title = await self.get_og_title(session)
			assert isinstance(title, str)
			return title, "og"
		except:
			pass

	async def get_html(self, session: Optional[SessionType] = None) -> Optional[str]:
		try:
			self.html = await request(self.url, session, headers = browser_agent, raise_for_status = True)
		except:
			pass
		return self.html

	async def get_og_title(self, session: Optional[SessionType] = None) -> Optional[str]:
		from bs4 import BeautifulSoup
		try:
			self.html = self.html or await self.get_html(session)
			assert self.html
			bs = BeautifulSoup(self.html, features = "lxml")
		except:
			return
		title = None
		try:
			meta: Any = bs.find("meta", property = "og:title")
			if t := meta.get("content"):
				title = t
		except:
			pass
		try:
			tag: Any = bs.title
			if t := tag.text:
				title = t
		except:
			pass
		if title:
			return re.sub(r" *\- Apple ?([(（]\S+[)）])?$", "", title).translate({0xa0: 0x20})

	async def get_aos_title(self, ensure: bool = True, session: Optional[SessionType] = None) -> Self:
		if not self.aos_data:
			await FulfillmentMessage(self, store = None, search_nearby = False, session = session, ensure = ensure)
		if self.aos_data:
			ref = next((v for v in self.aos_data.values() if self.partno in v.get("partsAvailability", {})), None)
			if not ref:
				return self
			t = ref["partsAvailability"][self.partno]["messageTypes"]["regular"]["storePickupProductTitle"]
			self.title = t.translate({0xa0: 0x20})
		return self

async def FulfillmentMessage(
	products: Product | list[Product],
	store: Optional[Store] = None,
	search_nearby: bool = False, timeout: int = 5,
	session: Optional[SessionType] = None, ensure: bool = True) -> list[Product]:
	products = [products] if isinstance(products, Product) else products
	if store is None:
		store = storeReturn(products[0].region.flag, opening = 1)[0]
	url = f"https://www.apple.com{store.region.url_store}/shop/fulfillment-messages"
	params = {"searchNearby": str(search_nearby).lower(), "store": store.rid}
	for p in products:
		await p.get_rich_partno(session = session)
	for ind, prod in enumerate(p for p in products if p.rich):
		params[f"parts.{ind}"] = prod.partno
	if len(params) == 2:
		if not ensure:
			raise ValueError("产品部件号码均不完整")
		return products
	r = await request(url, session, params = params, mode = "json",
		headers = browser_agent, retry = 3, timeout = timeout)
	body = r["body"]["content"]["pickupMessage"]
	for p in products:
		p.aos_data.update({s["storeNumber"]: s for s in body.get("stores", [])})
	return products

async def GenerateImage(urls: list[str], alpha: bool = False,
	session: Optional[SessionType] = None) -> Optional[bytes]:
	from io import BytesIO

	from PIL import Image

	async def get_image(url: str) -> Image.Image:
		if scale := url.startswith("SCALE"):
			url = url.removeprefix("SCALE")
		r = await request(url, session, mode = "raw", headers = browser_agent)
		base = Image.open(BytesIO(r))
		blank = Image.new("RGBA", (900, 900), color)
		if scale:
			prop = 1.5
			base = base.resize((int(900 / prop), int(900 / prop)))
			box = (int(450 * (1 - 1 / prop)), int(450 * (1 - 1 / prop)))
		else:
			width, height = base.size
			if width != height:
				starting  = max(width, height) - int(abs(width - height) / 2)
				matrix = (max(width - starting, 0), max(height - starting, 0), min(width, starting), min(height, starting))
				base = base.crop(matrix)
			base, box = base.resize((900, 900)), None
		blank.paste(base, box = box, mask = base if base.mode == "RGBA" else None)
		return blank

	if not urls:
		return
	color = (0, 0, 0, 0) if alpha else (255, 255, 255)
	tasks = {u: asyncio.create_task(get_image(u)) for u in set(urls)}
	await asyncio.wait(tasks.values())
	images = []
	for i in urls:
		try:
			images.append(tasks[i].result())
		except:
			logging.error(f"下载图片 URL {i} 失败: {tasks[i].exception()!r}")

	match (lenarr := len(images)):
		case 0:
			return
		case 1:
			image = Image.new("RGBA", (200 + 2000, 200 + 1000), color)
			image.paste(images[0], (500 + 150, 100 + 50))
		case 2 | 4:
			image = Image.new("RGBA", (200 + 2000, 200 + int(1000 * lenarr / 2)), color)
			for i, a in enumerate(images):
				h, l = int(i / 2), i % 2
				image.paste(a, (100 + 50 + 1000 * l, 100 + 50 + 1000 * h))
		case _:
			image = Image.new("RGBA", (200 + 3000, 200 + 1000 * (lenarr / 3).__ceil__()), color)
			for i, a in enumerate(images):
				h, l = int(i / 3), i % 3
				image.paste(a, (100 + 50 + 1000 * l, 100 + 50 + 1000 * h))

	result = BytesIO()
	image.save(result, "PNG")
	return result.getvalue()

def process_image_url(url: str) -> str:
	wo = url.split("?")[0]
	return f"{wo}?wid={(s := 1350 if "app-giveback-kit" in wo else 900)}&hei={s}&fmt=png"