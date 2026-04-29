from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import date
from typing import Any, Callable

from .hotel_api import get_hotel_details_api, search_hotels_api, web_search_api
from .models import BookingPhase, BookingState, HotelSummary


def search_hotels(
    state: BookingState,
    destination: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    currency: str = "USD",
) -> str:
    """Search for hotels at a destination. Returns a list of hotels with prices and ratings.

    Args:
        destination: City or area to search, e.g. "Paris, France".
        check_in_date: Check-in date in YYYY-MM-DD format.
        check_out_date: Check-out date in YYYY-MM-DD format.
        adults: Number of adult guests. Defaults to 2.
        currency: Currency code for prices, e.g. USD, EUR, GBP. Defaults to USD.

    Returns:
        JSON string of hotel results with names, prices, ratings, and amenities.
    """
    try:
        hotels = search_hotels_api(
            destination=destination,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            adults=adults,
            currency=currency,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})

    state.search_results = hotels
    state.phase = BookingPhase.PRESENTING

    results = []
    for i, h in enumerate(hotels[:5], 1):
        results.append({
            "number": i,
            "name": h.name,
            "price_per_night": h.price,
            "rating": h.rating,
            "stars": h.stars,
            "amenities": h.amenities[:3],
        })
    return json.dumps({"hotels": results, "total_found": len(hotels)})


def get_hotel_details(state: BookingState, property_token: str) -> str:
    """Get detailed information about a specific hotel from search results.

    Args:
        property_token: The property token from search results identifying the hotel.

    Returns:
        JSON string with full hotel details including amenities, reviews, nearby places, and prices from different sources.
    """
    check_in = state.check_in.isoformat() if state.check_in else ""
    check_out = state.check_out.isoformat() if state.check_out else ""

    try:
        details = get_hotel_details_api(
            property_token=property_token,
            check_in_date=check_in,
            check_out_date=check_out,
            currency=state.currency,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps(details)


def update_booking_state(
    state: BookingState,
    destination: str | None = None,
    check_in: str | None = None,
    check_out: str | None = None,
    guests: int | None = None,
    budget_max: float | None = None,
    currency: str | None = None,
    preferences: list[str] | None = None,
    phase: str | None = None,
    selected_hotel_name: str | None = None,
) -> str:
    """Update the current booking state with new information learned from the conversation.
    Call this whenever you learn new booking details from the user.

    Args:
        destination: Hotel destination city or area.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        guests: Number of guests.
        budget_max: Maximum budget per night in the specified currency.
        currency: Currency code, e.g. USD, EUR, GBP.
        preferences: List of preferences like pool, wifi, beach, gym.
        phase: Current booking phase: gathering_info, searching, presenting, selected, complete.
        selected_hotel_name: Name of the hotel the user selected.

    Returns:
        Confirmation of the updated booking state.
    """
    if destination is not None:
        state.destination = destination
    if check_in is not None:
        state.check_in = date.fromisoformat(check_in)
    if check_out is not None:
        state.check_out = date.fromisoformat(check_out)
    if guests is not None:
        state.guests = guests
    if budget_max is not None:
        state.budget_max = budget_max
    if currency is not None:
        state.currency = currency
    if preferences is not None:
        state.preferences = preferences
    if phase is not None:
        state.phase = BookingPhase(phase)
    if selected_hotel_name is not None:
        for h in state.search_results:
            if h.name.lower() == selected_hotel_name.lower():
                state.selected_hotel = h
                break

    return f"Booking state updated.\n{state.summary()}"


def web_search(state: BookingState, query: str) -> str:
    """Search the internet for real-time information. Use this for weather forecasts,
    local events, travel advisories, flight prices, restaurant recommendations,
    or any question that needs up-to-date information beyond your training data.

    Args:
        query: The search query, e.g. 'weather in Delhi May 15 2026' or 'best restaurants in Paris'.

    Returns:
        JSON string with search results including titles, snippets, and links.
    """
    try:
        results = web_search_api(query)
    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps({"results": results})


CODE_TIMEOUT = 30  # seconds


def run_python_code(state: BookingState, code: str) -> str:
    """Execute Python code and return the output. Use this when you need to:
    - Call an API that you don't have a dedicated tool for
    - Do calculations, data processing, or conversions
    - Fetch data from a URL using requests or urllib
    - Solve any problem that requires writing code

    The code runs in a separate process. Use print() to output results.
    You have access to: requests, json, math, datetime, urllib, and all standard library modules.

    Args:
        code: Python code to execute. Use print() to output results.

    Returns:
        The stdout output of the code, or error message if it failed.
    """
    # Guard against the model writing essays instead of code
    if len(code) > 2000:
        return json.dumps({
            "status": "error",
            "error": "Code too long. Write short, clean Python — no comments or explanations. Max 2000 characters.",
        })

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        f.flush()

        try:
            result = subprocess.run(
                ["python3", f.name],
                capture_output=True,
                text=True,
                timeout=CODE_TIMEOUT,
            )

            output = result.stdout.strip()
            errors = result.stderr.strip()

            if result.returncode != 0:
                return json.dumps({
                    "status": "error",
                    "error": errors or "Code failed with no error message",
                    "output": output,
                })

            return json.dumps({
                "status": "success",
                "output": output or "(no output — did you forget to print?)",
            })

        except subprocess.TimeoutExpired:
            return json.dumps({
                "status": "error",
                "error": f"Code timed out after {CODE_TIMEOUT} seconds",
            })


# Tool definitions for Ollama (JSON schema format)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_hotels",
            "description": (
                "Search for hotels at a destination. "
                "Returns a list of hotels with prices and ratings."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "City or area to search, e.g. 'Paris, France'",
                    },
                    "check_in_date": {
                        "type": "string",
                        "description": "Check-in date in YYYY-MM-DD format",
                    },
                    "check_out_date": {
                        "type": "string",
                        "description": "Check-out date in YYYY-MM-DD format",
                    },
                    "adults": {
                        "type": "integer",
                        "description": "Number of adult guests (default 2)",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code for prices (default USD)",
                    },
                },
                "required": ["destination", "check_in_date", "check_out_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hotel_details",
            "description": (
                "Get detailed information about a specific hotel. "
                "Use the property_token from search results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "property_token": {
                        "type": "string",
                        "description": "The property token from search results",
                    },
                },
                "required": ["property_token"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_booking_state",
            "description": (
                "Update the current booking state with new information learned from the user. "
                "Call this whenever you learn new booking details like destination, dates, "
                "budget, or preferences."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Hotel destination city or area",
                    },
                    "check_in": {
                        "type": "string",
                        "description": "Check-in date YYYY-MM-DD",
                    },
                    "check_out": {
                        "type": "string",
                        "description": "Check-out date YYYY-MM-DD",
                    },
                    "guests": {
                        "type": "integer",
                        "description": "Number of guests",
                    },
                    "budget_max": {
                        "type": "number",
                        "description": "Maximum budget per night",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code (e.g. USD, EUR)",
                    },
                    "preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of preferences like pool, wifi, beach",
                    },
                    "phase": {
                        "type": "string",
                        "enum": [
                            "gathering_info",
                            "searching",
                            "presenting",
                            "selected",
                            "complete",
                        ],
                        "description": "Current booking phase",
                    },
                    "selected_hotel_name": {
                        "type": "string",
                        "description": "Name of the hotel the user selected",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the internet for real-time information. "
                "Use this for weather, local events, travel advisories, "
                "flight prices, restaurant recommendations, or any question "
                "that needs current information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_code",
            "description": (
                "Execute Python code to solve problems, call APIs, "
                "do calculations, or fetch data from URLs. "
                "Use this when no other tool fits the question. "
                "Use print() to output results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute. Use print() for output.",
                    },
                },
                "required": ["code"],
            },
        },
    },
]


# Registry mapping tool names to callables
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "search_hotels": search_hotels,
    "get_hotel_details": get_hotel_details,
    "update_booking_state": update_booking_state,
    "web_search": web_search,
    "run_python_code": run_python_code,
}


def execute_tool(name: str, arguments: dict[str, Any], state: BookingState) -> str:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return fn(state=state, **arguments)
