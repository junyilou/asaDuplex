import re
from typing import Any, Optional, Self

from aiohttp import ClientResponseError

from modules.util import (AsyncRetry, RetryExceeded, RetrySignal, SessionType,
                          request)


class MiniProgram:
	def __init__(self) -> None:
		self.prefix: str = ""

	def __repr__(self) -> str:
		return f"<MiniProgram {self.prefix.removesuffix("/") or "N/A"}>"

	@property
	def headers(self) -> dict[str, str]:
		agents = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0_1 like Mac OS X)",
			"AppleWebKit/605.1.15 (KHTML, like Gecko)",
			"MicroMessenger/8.0.53(0x1800352b)", "NetType/WIFI Language/zh_CN")
		return {"User-Agent": " ".join(agents)}

	async def init(self, session: Optional[SessionType] = None) -> Self:
		r = await self.request("miniprogram-merch/p/wechat/init", session, assert_keyword = "urls")
		rule = r"(?<=https://web\.mmap\.apple\.com/)[\d\.]*?(?=/miniprogram/)"
		prefix = next((r.group() for u in r["urls"].values() if (r := re.search(rule, u))), "")
		self.prefix = f"{prefix}{"/" if prefix else ""}"
		return self

	async def request(self, url: str, session: Optional[SessionType] = None,
		assert_keyword: Optional[str] = None, retry: int = 3, sleep: int = 1, **kwargs) -> Any:
		build_url = f"https://web.mmap.apple.com/{self.prefix}{url}"
		@AsyncRetry(retry, sleep)
		async def decorate() -> Any:
			try:
				r = await request(build_url, session, headers = self.headers,
					ssl = False, mode = "json", raise_for_status = True, **kwargs)
				if assert_keyword:
					assert assert_keyword in r, f"Essential key {assert_keyword!r} missing"
				return r
			except ClientResponseError as ce:
				raise RetrySignal(ValueError(f"HTTP {ce.status}: {ce.message}"))
			except Exception as exp:
				raise RetrySignal(exp)
		try:
			return await decorate()
		except RetryExceeded as re:
			raise re.exp

async def Mini(session: Optional[SessionType] = None) -> MiniProgram:
	return await MiniProgram().init(session)