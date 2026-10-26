import httpx


BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

FUELHH_ENDPOINT = f"{BASE_URL}/datasets/FUELHH/stream"


async def fetch_fuelhh_actuals(
    settlement_date_from: str,
    settlement_date_to: str,
    fuel_type: str = "WIND",
) -> list[dict]:
    """
    Fetch actual generation records from the Elexon FUELHH dataset.

    Args:
        settlement_date_from: Starting settlement date, YYYY-MM-DD.
        settlement_date_to: Ending settlement date, YYYY-MM-DD.
        fuel_type: Fuel type to retrieve. Defaults to WIND.

    Returns:
        A list of generation records returned by Elexon.

    Raises:
        httpx.HTTPStatusError: If Elexon returns an unsuccessful HTTP status.
        httpx.RequestError: If the request cannot reach Elexon.
        ValueError: If Elexon returns an unexpected response structure.
    """
    params = {
        "settlementDateFrom": settlement_date_from,
        "settlementDateTo": settlement_date_to,
        "fuelType": fuel_type,
    }

    headers = {
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            FUELHH_ENDPOINT,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            "Unexpected Elexon response: expected a JSON list."
        )

    return data
