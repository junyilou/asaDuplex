from typing import Any, Optional
from modules.util import SessionType

async def async_post(json: dict[str, Any], session: Optional[SessionType] = None) -> Optional[dict[str, Any]]:
	from os import environ
	from modules.util import request
	try:
		API = environ["BOTPOST_API"]
		return await request(API, session, "POST", json = json, mode = "json", ssl = False, raise_for_status = True)
	except KeyError:
		raise KeyError("[获取地址失败] 环境变量中找不到地址") from None
	except Exception as exp:
		import logging
		return logging.error(f"[通知推送失败] {exp!r}")

def photo_encode(r: bytes) -> str:
	from base64 import b64encode
	return "BASE64" + b64encode(r).decode()