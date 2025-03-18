from asyncio import sleep
from collections.abc import Generator, Iterable, Mapping
from datetime import datetime, timedelta
from random import randint
from typing import Any, Literal, Optional

from modules.store import FulfillmentMessage, Product
from modules.util import AsyncRetry, RetryExceeded, RetrySignal, SessionType
from storeInfo import Store

dayOfWeek = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

def convert(dct: Mapping[str, Any], lang: bool = True) -> str:
	match dct:
		case {"openTime": "00:00:00", "closeTime": "23:59:00"}:
			return "24 小时营业" if lang else "Always Open"
		case {"openTime": opt, "closeTime": clt}:
			return f"{opt[:5]} - {clt[:5]}"
		case {"formattedTime": _}:
			return "不营业" if lang else "Closed"
		case _:
			return "未知时间" if lang else "Unknown Hours"

def ignored(converted: dict[str, str], rules: dict[str, str]) -> Generator[tuple[str, str]]:
	for date, data in converted.items():
		if rules.get(date) == data:
			continue
		if rules.get(dayOfWeek[datetime.strptime(date, "%Y-%m-%d").weekday()]) == data:
			continue
		yield date, data

async def base_comment(store: Store,
	accepted_dates: Iterable[str],
	force_return: bool,
	results_dict: dict[str, dict[str, str]],
	timeout: int, session: Optional[SessionType]) -> dict[str, dict[str, str]]:
	try:
		assert store.region.url_store is not None
		assert store.region.part_sample
		assert store.region.apu
		prod = Product(store.region.part_sample, store.region)
	except:
		if force_return:
			return {store.rid: {}}
		return {}
	try:
		await FulfillmentMessage(prod, store, search_nearby = True,
			timeout = timeout, session = session, ensure = True)
		assert prod.aos_data
	except Exception:
		return results_dict
	for rid, rstore in prod.aos_data.items():
		if force_return:
			results_dict.setdefault(rid, {})
		for holiday in rstore["retailStore"]["storeHolidays"]:
			raw = datetime.strptime(f"{holiday["date"]} 2000", "%b %d %Y")
			try:
				raw = raw.replace(year = datetime.now().year)
				assert raw > datetime.now() - timedelta(weeks = 1)
			except:
				raw = raw.replace(year = raw.year + 1)
			date_str = raw.strftime("%F")
			if accepted_dates and date_str not in accepted_dates:
				continue
			text = f"{f"[{d}] " if (d := holiday["description"]) else ""}{holiday["comments"] or ""}"
			results_dict.setdefault(rid, {})[date_str] = text
	return results_dict

async def comment(store: Store,
	accepted_dates: Iterable[str] = [],
	force_return: bool = False,
	results_dict: dict[str, dict[str, str]] = {},
	session: Optional[SessionType] = None,
	max_retry: int = 3, timeout: int = 5,
	min_interval: int = 2, max_interval: int = 8,
	shout: bool = False) -> dict[str, dict[str, str]]:
	@AsyncRetry(max_retry)
	async def decorate() -> dict[str, dict[str, str]]:
		try:
			return await base_comment(store, accepted_dates, force_return, results_dict, timeout, session)
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
	ignore_same: bool = False,
	detail: dict[str, list[dict[str, Any]]] = {},
	rules: dict[str, str] = {},
	session: Optional[SessionType] = None) -> Optional[dict[str, dict[str, str]]]:
	threshold = threshold or datetime.now()
	if not detail:
		detail = await store.detail(session = session)
	for key in ("hoursData", "specialHours"):
		assert key in detail

	comments, results, asked = {}, {}, []
	regular = {dayOfWeek.index(h["dayOfWeek"]): convert(h["time"]) for h in detail["hoursData"]}
	converted = {d["date"]: convert(d["time"], lang = False) for d in detail["specialHours"]}
	for date, converted in ignored(converted, rules = rules):
		d = datetime.strptime(date, "%Y-%m-%d")
		if date < f"{threshold:%F}":
			continue
		reg = regular[d.weekday()]
		if ignore_same and reg == converted:
			continue
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