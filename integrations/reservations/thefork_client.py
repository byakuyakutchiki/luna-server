"""
TheFork (LaFourchette) - Reservation de restaurants

Utilise l'API TheFork Partner pour rechercher et reserver des restaurants.
L'exploitant obtient ses cles via le programme partenaire TheFork.

Env vars:
    THEFORK_API_KEY     - Cle API partenaire
    THEFORK_ENV         - "test" ou "production" (default: test)

Fallback: si TheFork non configure, Luna utilise search_places + call_contact
pour trouver un restaurant et appeler pour reserver.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

BASE_URLS = {
    "test": "https://api.lafourchette.com/api",
    "production": "https://api.thefork.com/api",
}


class TheForkClient:
    def __init__(self, api_key: str, env: str = "test"):
        self.api_key = api_key
        self.base_url = BASE_URLS.get(env, BASE_URLS["test"])

    @classmethod
    def from_env(cls) -> "TheForkClient":
        api_key = os.getenv("THEFORK_API_KEY", "")
        env = os.getenv("THEFORK_ENV", "test")
        if not api_key:
            logger.info("THEFORK_API_KEY non configuree — reservations restaurants via TheFork desactivees")
        return cls(api_key=api_key, env=env)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search_restaurants(
        self,
        city: str,
        date: str,
        time: str = "20:00",
        party_size: int = 2,
        cuisine: Optional[str] = None,
        max_results: int = 5,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recherche de restaurants avec disponibilite.

        Args:
            city: Ville (ex: "Paris", "Lyon")
            date: Date YYYY-MM-DD
            time: Heure HH:MM (default 20:00)
            party_size: Nombre de convives
            cuisine: Type de cuisine (optionnel)
            max_results: Nombre max

        Returns:
            (True, {"restaurants": [...]}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {
                "error": "TheFork non configure. Luna peut chercher un restaurant avec search_places et appeler pour reserver avec call_contact.",
                "fallback": "search_places"
            }

        try:
            params = {
                "key": self.api_key,
                "city": city,
                "date": date,
                "time": time,
                "party_size": party_size,
                "limit": max_results,
            }
            if cuisine:
                params["cuisine"] = cuisine

            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.get(f"{self.base_url}/restaurants/search", params=params)

            if resp.status_code != 200:
                logger.warning(f"TheFork search failed: {resp.status_code}")
                return False, {"error": "Erreur de recherche TheFork", "fallback": "search_places"}

            data = resp.json()
            restaurants = []

            for r in data.get("data", data.get("restaurants", []))[:max_results]:
                restaurant = {
                    "id": r.get("id", ""),
                    "name": r.get("name", ""),
                    "cuisine": r.get("cuisine_type", r.get("cuisine", "")),
                    "rating": r.get("rating", r.get("avg_rate", "")),
                    "price_range": r.get("price_range", r.get("avg_price", "")),
                    "address": r.get("address", ""),
                    "phone": r.get("phone", ""),
                    "available": r.get("has_availability", True),
                    "discount": r.get("discount", r.get("special_offer", "")),
                }
                restaurant["summary"] = (
                    f"{restaurant['name']}"
                    f" ({restaurant['cuisine']})" if restaurant['cuisine'] else ""
                    f" — Note: {restaurant['rating']}/10" if restaurant['rating'] else ""
                    f" — {restaurant['address']}"
                )
                restaurants.append(restaurant)

            return True, {
                "restaurants": restaurants,
                "count": len(restaurants),
                "city": city,
                "date": date,
                "time": time,
                "party_size": party_size,
            }

        except Exception as e:
            logger.error(f"TheFork error: {e}")
            return False, {"error": str(e), "fallback": "search_places"}

    async def book_restaurant(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        party_size: int,
        customer_name: str,
        customer_phone: str,
        customer_email: str = "",
        special_requests: str = "",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reserve une table.

        Returns:
            (True, {"confirmation": "...", "booking_id": "..."}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "TheFork non configure", "fallback": "call_contact"}

        try:
            payload = {
                "key": self.api_key,
                "restaurant_id": restaurant_id,
                "date": date,
                "time": time,
                "party_size": party_size,
                "customer": {
                    "first_name": customer_name.split()[0] if customer_name else "",
                    "last_name": " ".join(customer_name.split()[1:]) if len(customer_name.split()) > 1 else "",
                    "phone": customer_phone,
                    "email": customer_email,
                },
                "special_requests": special_requests,
            }

            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(f"{self.base_url}/bookings", json=payload)

            if resp.status_code in (200, 201):
                data = resp.json()
                return True, {
                    "booking_id": data.get("id", data.get("booking_id", "")),
                    "confirmation": f"Reservation confirmee pour {party_size} personne(s) le {date} a {time}",
                    "restaurant_name": data.get("restaurant_name", ""),
                }
            else:
                return False, {"error": f"Reservation echouee (HTTP {resp.status_code})", "fallback": "call_contact"}

        except Exception as e:
            logger.error(f"TheFork booking error: {e}")
            return False, {"error": str(e), "fallback": "call_contact"}

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "service": "TheFork",
        }
