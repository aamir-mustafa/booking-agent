from __future__ import annotations

import os

import httpx

from .models import HotelSummary

SERPAPI_BASE = "https://serpapi.com/search"


def _get_api_key() -> str:
    key = os.environ.get("SERPAPI_API_KEY", "")
    if not key:
        raise RuntimeError(
            "SERPAPI_API_KEY is not set. "
            "Get a free key at https://serpapi.com and add it to your .env file."
        )
    return key


def search_hotels_api(
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    currency: str = "USD",
    gl: str = "us",
    hl: str = "en",
) -> list[HotelSummary]:
    params = {
        "engine": "google_hotels",
        "q": destination,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "currency": currency,
        "gl": gl,
        "hl": hl,
        "api_key": _get_api_key(),
    }

    resp = httpx.get(SERPAPI_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    properties = data.get("properties", [])
    hotels: list[HotelSummary] = []
    for prop in properties:
        rate = prop.get("rate_per_night", {})
        hotels.append(
            HotelSummary(
                name=prop.get("name", "Unknown"),
                price=rate.get("lowest"),
                rating=prop.get("overall_rating"),
                stars=prop.get("extracted_hotel_class"),
                amenities=prop.get("amenities", []),
                address=prop.get("description", ""),
                property_token=prop.get("property_token"),
                thumbnail=(prop.get("images", [{}])[0].get("thumbnail")
                           if prop.get("images") else None),
            )
        )
    return hotels


def web_search_api(query: str) -> list[dict]:
    params = {
        "engine": "google",
        "q": query,
        "api_key": _get_api_key(),
    }

    resp = httpx.get(SERPAPI_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    results = []
    # Answer box (direct answer from Google)
    if "answer_box" in data:
        box = data["answer_box"]
        results.append({
            "type": "answer_box",
            "title": box.get("title", ""),
            "answer": box.get("answer") or box.get("snippet", ""),
        })

    # Knowledge graph
    if "knowledge_graph" in data:
        kg = data["knowledge_graph"]
        results.append({
            "type": "knowledge_graph",
            "title": kg.get("title", ""),
            "description": kg.get("description", ""),
        })

    # Top organic results
    for item in data.get("organic_results", [])[:5]:
        results.append({
            "type": "search_result",
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": item.get("link", ""),
        })

    return results


def get_hotel_details_api(
    property_token: str,
    check_in_date: str = "",
    check_out_date: str = "",
    currency: str = "USD",
) -> dict:
    params = {
        "engine": "google_hotels",
        "property_token": property_token,
        "currency": currency,
        "api_key": _get_api_key(),
    }
    if check_in_date:
        params["check_in_date"] = check_in_date
    if check_out_date:
        params["check_out_date"] = check_out_date

    resp = httpx.get(SERPAPI_BASE, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    props = data.get("properties", [])
    if not props:
        return {"error": "No details found for this property."}

    prop = props[0]
    rate = prop.get("rate_per_night", {})
    total = prop.get("total_rate", {})

    return {
        "name": prop.get("name", "Unknown"),
        "description": prop.get("description", ""),
        "address": prop.get("description", ""),
        "overall_rating": prop.get("overall_rating"),
        "reviews_count": prop.get("reviews"),
        "hotel_class": prop.get("hotel_class"),
        "check_in_time": prop.get("check_in_time"),
        "check_out_time": prop.get("check_out_time"),
        "rate_per_night": rate.get("lowest"),
        "total_rate": total.get("lowest"),
        "amenities": prop.get("amenities", []),
        "nearby_places": [
            {
                "name": p.get("name"),
                "transport": [
                    f"{t.get('type')}: {t.get('duration')}"
                    for t in p.get("transportations", [])
                ],
            }
            for p in prop.get("nearby_places", [])
        ],
        "prices": [
            {"source": p.get("source"), "rate": p.get("rate_per_night", {}).get("lowest")}
            for p in prop.get("prices", [])
        ],
    }
