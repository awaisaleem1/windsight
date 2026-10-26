import httpx

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
WINDFOR_ENDPOINT = f"{BASE_URL}/datasets/WINDFOR/stream"


async def fetch_wind_forecasts(
    publish_time_from: str,
    publish_time_to: str,
) -> list[dict]:
    """
    Fetch historical wind generation forecasts from Elexon WINDFOR.

    Args:
        publish_time_from: Start of the forecast publication window.
        publish_time_to: End of the forecast publication window.

    Returns:
        A list of forecast records.
    """
    params = {
        "publishDateTimeFrom": publish_time_from,
        "publishDateTimeTo": publish_time_to,
    }

    headers = {
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=60.0,
        follow_redirects=True,
    ) as client:
        response = await client.get(
            WINDFOR_ENDPOINT,
            params=params,
            headers=headers,
        )

        response.raise_for_status()
        data = response.json()

    if not isinstance(data, list):
        raise ValueError(
            "Unexpected Elexon WINDFOR response: expected a JSON list."
        )

    return data
