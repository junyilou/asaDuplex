from asyncio import sleep
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timedelta
from random import randint
from typing import Any, Literal, Optional

from modules.util import (AsyncRetry, RetryExceeded, RetrySignal, SessionType,
                          browser_agent, request)
from storeInfo import Store

dayOfWeek = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def convert(dct: Mapping[str, Any], userLang: bool = True) -> str:
	match dct:
		case {"closed": True}:
			return "不营业" if userLang else "Closed"
		case {"openTime": "00:00", "closeTime": "23:59"}:
			return "24 小时营业" if userLang else "Always Open"
		case {"openTime": opt, "closeTime": clt}:
			return f"{opt} - {clt}"
		case _:
			return "未知时间" if userLang else "Unknown Hours"

def ignored(
	data: list[dict[str, Any]],
	rules: dict[str, str],
	userLang: bool = True) -> Iterator[tuple[str, str]]:
	for item in sorted(data, key = lambda k: k["date"]):
		converted = convert(item, userLang)
		try:
			for key in ("date", "name"):
				assert converted != rules.get(item[key])
		except:
			continue
		yield item["date"], converted

async def base_comment(store: Store,
	accepted_dates: Iterable[str],
	results_dict: dict[str, dict[str, str]],
	timeout: int, session: Optional[SessionType]) -> dict[str, dict[str, str]]:
	if not store.region.url_store or not store.region.part_sample:
		return {}
	base = f"https://www.apple.com{store.region.url_store}"
	url = f"{base}/shop/fulfillment-messages"
	referer = browser_agent | {"Referer": f"{base}/shop/product/{store.region.part_sample}"}
	params = {"searchNearby": "true", "store": store.rid, "parts.0": store.region.part_sample}

	stores: list[dict] = []
	r = await request(url, session, headers = referer, timeout = timeout,
		params = params, raise_for_status = True, mode = "json")
	try:
		stores = r["body"]["content"]["pickupMessage"]["stores"]
	except KeyError:
		return results_dict
	for rstore in stores:
		for holiday in rstore["retailStore"]["storeHolidays"]:
			rid = rstore["storeNumber"]
			raw = datetime.strptime(f"{holiday["date"]} 2000", "%b %d %Y")
			try:
				raw = raw.replace(year = datetime.now().year)
				assert raw > datetime.now() - timedelta(weeks = 1)
			except:
				raw = raw.replace(year = raw.year + 1)
			date_str = raw.strftime("%F")
			if accepted_dates and date_str not in accepted_dates:
				continue
			text = " ".join(i for i in (f"[{holiday["description"] or ""}]", holiday["comments"]) if i)
			results_dict.setdefault(rid, {})[date_str] = text
	return results_dict

async def comment(store: Store,
	accepted_dates: Iterable[str] = [],
	results_dict: dict[str, dict[str, str]] = {},
	session: Optional[SessionType] = None,
	max_retry: int = 3, timeout: int = 5,
	min_interval: int = 2, max_interval: int = 8,
	shout: bool = False) -> dict[str, dict[str, str]]:
	@AsyncRetry(max_retry)
	async def decorate() -> dict[str, dict[str, str]]:
		try:
			return await base_comment(store, accepted_dates, results_dict, timeout, session)
		except Exception as exp:
			await sleep(randint(min_interval, max_interval))
			raise RetrySignal(exp)
	try:
		return await decorate()
	except RetryExceeded as re:
		if not shout:
			return results_dict
		raise re.exp from None

async def special(store: Store, *,
	threshold: Optional[datetime] = None,
	ask_comment: bool = True,
	userLang: bool = True,
	detail: dict[str, list[dict[str, Any]]] = {},
	rules: dict[str, str] = {},
	session: Optional[SessionType] = None) -> Optional[dict[str, dict[str, str]]]:
	threshold = threshold or datetime.now()
	if not detail:
		try:
			detail = await store.detail(session = session, mode = "hours")
			assert isinstance(detail, dict)
			for key in ("regular", "special"):
				assert key in detail
		except:
			return

	comments, results, asked = {}, {}, []
	regular = {dayOfWeek.index(regular["name"]): convert(regular, userLang = userLang) for regular in detail["regular"]}
	for date, converted in ignored(detail["special"], rules = rules, userLang = userLang):
		d = datetime.strptime(date, "%Y-%m-%d")
		if date < f"{threshold:%F}":
			continue
		reg = regular[d.weekday()]
		try:
			assert ask_comment
			assert store.rid not in comments
			assert store.rid not in asked
			comments = await comment(store, results_dict = comments, session = session)
		except:
			pass
		finally:
			asked.append(store.rid)
		com = comments.get(store.rid, {}).get(date)
		results[f"{d:%F}"] = {"regular": reg, "special": converted} | ({"comment": com} if com else {})
	return results

type ResultType = tuple[str, Literal["new", "change", "comment", "outdated", "cancel"], *tuple[str, ...]]

def compare(
	original: dict[str, dict[str, str]],
	current: dict[str, dict[str, str]],
	threshold: str = "") -> list[ResultType]:
	diff: list[ResultType] = []
	for date, detail in current.items():
		spe = detail["special"]
		if date < threshold:
			continue
		if date not in original:
			diff.append((date, "new", spe))
		elif (svd := original[date]["special"]) != spe:
			diff.append((date, "change", svd, spe))
		elif not original[date].get("comment") and detail.get("comment"):
			diff.append((date, "comment", detail["comment"]))
	for date, detail in original.items():
		if date < threshold:
			diff.append((date, "outdated"))
		elif date not in current:
			diff.append((date, "cancel", detail["special"]))
	return sorted(diff)