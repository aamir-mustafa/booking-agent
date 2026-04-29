from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class BookingPhase(str, Enum):
    GATHERING_INFO = "gathering_info"
    SEARCHING = "searching"
    PRESENTING = "presenting"
    SELECTED = "selected"
    COMPLETE = "complete"


class HotelSummary(BaseModel):
    name: str
    price: Optional[str] = None
    rating: Optional[float] = None
    stars: Optional[int] = None
    amenities: list[str] = []
    address: Optional[str] = None
    property_token: Optional[str] = None
    thumbnail: Optional[str] = None


class BookingState(BaseModel):
    destination: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    guests: int = 1
    budget_max: Optional[float] = None
    currency: str = "USD"
    preferences: list[str] = []
    search_results: list[HotelSummary] = []
    selected_hotel: Optional[HotelSummary] = None
    phase: BookingPhase = BookingPhase.GATHERING_INFO

    def summary(self) -> str:
        lines = []
        lines.append(f"Phase: {self.phase.value}")
        lines.append(f"Destination: {self.destination or 'not set'}")
        lines.append(f"Check-in: {self.check_in or 'not set'}")
        lines.append(f"Check-out: {self.check_out or 'not set'}")
        lines.append(f"Guests: {self.guests}")
        if self.budget_max:
            lines.append(f"Budget max: {self.budget_max} {self.currency}/night")
        if self.preferences:
            lines.append(f"Preferences: {', '.join(self.preferences)}")
        if self.search_results:
            lines.append(f"Search results ({len(self.search_results)} hotels):")
            for i, h in enumerate(self.search_results[:5], 1):
                parts = [f"  {i}. {h.name}"]
                if h.price:
                    parts.append(f"- {h.price}/night")
                if h.rating:
                    parts.append(f"- rating {h.rating}")
                if h.stars:
                    parts.append(f"- {h.stars} stars")
                lines.append(" ".join(parts))
        if self.selected_hotel:
            lines.append(f"Selected: {self.selected_hotel.name}")
        return "\n".join(lines)
