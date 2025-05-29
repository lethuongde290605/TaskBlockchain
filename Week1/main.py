import requests
import json

PRICE_URL = 'https://lite-api.jup.ag/price/v2'
TOKEN_URL = 'https://lite-api.jup.ag/tokens/v1'
HEADERS = {"Accept": "application/json"}


def get_tagged_tokens():
    url = f"{TOKEN_URL}/tagged/verified"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def get_token_prices(token_symbol: str):
    tagged = get_tagged_tokens()

    mint = None
    for token in tagged:
        if token.get("symbol") == token_symbol:
            mint = token.get("address")
            break

    if mint is None:
        raise ValueError(f"Token symbol '{token_symbol}' not found in tagged tokens.")

    url = f"{PRICE_URL}?ids={mint}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    response_json = response.json()
    data = response_json.get("data", {})

    if mint not in data:
        raise ValueError(f"Price data not found for mint: {mint}")

    return float(data[mint].get("price"))



if __name__ == "__main__":
    try:
        token_symbol = input("Input a token symbol: ")
        price_info = get_token_prices(token_symbol)
        print(f"Price of {token_symbol}: {price_info}")
    except Exception as e:
        print("Lỗi:", e)
