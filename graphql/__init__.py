import json
from typing import Any
from urllib.parse import quote

with open("graphql/table.json") as r:
	TABLE = json.load(r)

def generate_params(operation: str, variables: dict[str, Any]) -> str:
	params = {"operationName": operation, "variables": variables,
		"extensions": {"persistedQuery": {"version": 1, "sha256Hash": TABLE[operation]}}}
	formatted: dict[str, str] = {}
	for k, v in params.items():
		if isinstance(v, dict):
			formatted[k] = json.dumps(v, ensure_ascii = False, separators = (",", ":"))
		else:
			formatted[k] = str(v)
	params_str = "&".join(f"{k}={quote(v)}" for k, v in formatted.items())
	return params_str

def cleanup(data: dict[str, Any]) -> dict[str, Any]:
	def remove_typename(obj: Any) -> Any:
		if isinstance(obj, dict):
			return {k: remove_typename(v) for k, v in obj.items() if k != "__typename"}
		elif isinstance(obj, list):
			return [remove_typename(item) for item in obj]
		return obj
	return remove_typename(data)

APOLLO_HEADERS = {
	"apollographql-client-name": "Retail Store Pages",
	"apollographql-client-version": "4.1.0",
	"content-type": "application/json"}

ENDPOINT = "https://www.apple.com/api-www/graphql?"