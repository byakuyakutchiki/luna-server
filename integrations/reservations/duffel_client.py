"""
Duffel API Client - Vols et Hotels (reservation directe)

Luna peut rechercher ET reserver des vols/hotels directement via Duffel.
Le Traveller ne quitte jamais l'app — ses infos profil sont pre-remplies.

Env vars:
    DUFFEL_ACCESS_TOKEN  - Token API (test: duffel_test_xxx, live: duffel_live_xxx)

Pricing:
    - 0 EUR/mois (pay-as-you-go)
    - 3$/reservation vol + 1% Managed Content
    - Profit share sur hotels

Usage:
    client = DuffelClient.from_env()
    flights = await client.search_flights("Paris", "Nice", "2026-04-01")
    order = await client.book_flight(offer_id, passenger_info)
"""
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

import httpx

from core.settings import get_settings

logger = logging.getLogger(__name__)

DUFFEL_API_URL = "https://api.duffel.com"

# Codes IATA villes courantes
CITY_IATA = {
    "paris": "CDG", "lyon": "LYS", "marseille": "MRS", "toulouse": "TLS",
    "nice": "NCE", "nantes": "NTE", "strasbourg": "SXB", "montpellier": "MPL",
    "bordeaux": "BOD", "lille": "LIL", "rennes": "RNS", "grenoble": "GNB",
    "ajaccio": "AJA", "bastia": "BIA", "perpignan": "PGF", "pau": "PUF",
    "biarritz": "BIQ", "la reunion": "RUN",
    "londres": "LHR", "london": "LHR", "bruxelles": "BRU", "amsterdam": "AMS",
    "rome": "FCO", "milan": "MXP", "barcelone": "BCN", "madrid": "MAD",
    "lisbonne": "LIS", "berlin": "BER", "new york": "JFK", "montreal": "YUL",
    "marrakech": "RAK", "tunis": "TUN", "alger": "ALG", "dakar": "DSS",
    "dubai": "DXB", "tokyo": "NRT", "bangkok": "BKK", "istanbul": "IST",
}


class DuffelClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self._is_test = access_token.startswith("duffel_test_")

    @classmethod
    def from_env(cls) -> "DuffelClient":
        token = os.getenv("DUFFEL_ACCESS_TOKEN", "")
        if not token:
            logger.info("DUFFEL_ACCESS_TOKEN non configure — reservations Duffel desactivees")
        return cls(access_token=token)

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token)

    @property
    def is_test(self) -> bool:
        return self._is_test

    def _headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _api_request(self, method: str, path: str, json_data: Optional[Dict] = None) -> Optional[Dict]:
        """Requete authentifiee vers l'API Duffel."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as http:
                resp = await http.request(
                    method=method,
                    url=f"{DUFFEL_API_URL}{path}",
                    headers=self._headers(),
                    json=json_data,
                )
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                error_body = resp.text[:500]
                logger.warning(f"Duffel {method} {path} → {resp.status_code}: {error_body}")
                return None
        except Exception as e:
            logger.error(f"Duffel API error: {type(e).__name__}: {e}")
            return None

    def resolve_city_code(self, city_name: str) -> str:
        """Resout un nom de ville en code IATA aeroport."""
        normalized = city_name.lower().strip()
        if normalized in CITY_IATA:
            return CITY_IATA[normalized]
        if len(city_name) == 3 and city_name.isalpha():
            return city_name.upper()
        return city_name.upper()[:3]

    # =========================================================================
    # RECHERCHE DE VOLS
    # =========================================================================

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        passengers: int = 1,
        cabin_class: str = "economy",
        max_results: int = 8,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recherche de vols via Duffel.

        Returns:
            (True, {"flights": [...]}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "Duffel non configure."}

        origin_code = self.resolve_city_code(origin)
        dest_code = self.resolve_city_code(destination)

        slices = [
            {"origin": origin_code, "destination": dest_code, "departure_date": departure_date}
        ]
        if return_date:
            slices.append(
                {"origin": dest_code, "destination": origin_code, "departure_date": return_date}
            )

        passengers_list = [{"type": "adult"} for _ in range(passengers)]

        payload = {
            "data": {
                "slices": slices,
                "passengers": passengers_list,
                "cabin_class": cabin_class,
            }
        }

        result = await self._api_request("POST", "/air/offer_requests", payload)
        if not result:
            return False, {"error": "Impossible de rechercher les vols. Reessaie."}

        offers = (result.get("data") or {}).get("offers", [])
        if not offers:
            return True, {
                "flights": [],
                "message": f"Aucun vol {origin} → {destination} le {departure_date}.",
            }

        flights = []
        for offer in offers[:max_results]:
            slices_data = offer.get("slices", [])
            total_amount = offer.get("total_amount", "0")
            total_currency = offer.get("total_currency", "EUR")

            segments_info = []
            for sl in slices_data:
                for seg in sl.get("segments", []):
                    dep = seg.get("departing_at", "")
                    arr = seg.get("arriving_at", "")
                    _orig = seg.get("origin") or {}
                    _dest = seg.get("destination") or {}
                    _carrier = seg.get("marketing_carrier") or {}
                    _aircraft = seg.get("aircraft") or {}
                    segments_info.append({
                        "departure": _orig.get("iata_code", ""),
                        "departure_city": _orig.get("city_name", ""),
                        "departure_time": dep.split("T")[1][:5] if "T" in dep else "",
                        "arrival": _dest.get("iata_code", ""),
                        "arrival_city": _dest.get("city_name", ""),
                        "arrival_time": arr.split("T")[1][:5] if "T" in arr else "",
                        "carrier": _carrier.get("name", ""),
                        "carrier_code": _carrier.get("iata_code", ""),
                        "flight_number": seg.get("marketing_carrier_flight_number", ""),
                        "duration": seg.get("duration", ""),
                        "aircraft": _aircraft.get("name", ""),
                    })

            flight_info = {
                "id": offer.get("id", ""),
                "price": f"{total_amount} {total_currency}",
                "price_amount": float(total_amount),
                "price_currency": total_currency,
                "segments": segments_info,
                "cabin_class": cabin_class,
                "passengers_count": passengers,
                "bookable": True,
            }

            # Resume lisible
            if segments_info:
                first = segments_info[0]
                last = segments_info[-1]
                stops = len(segments_info) - 1
                stops_text = "direct" if stops == 0 else f"{stops} escale{'s' if stops > 1 else ''}"
                carrier_name = first.get("carrier", first.get("carrier_code", ""))
                flight_info["summary"] = (
                    f"{carrier_name} — {first['departure']} {first['departure_time']} → "
                    f"{last['arrival']} {last['arrival_time']} ({stops_text}) — "
                    f"{total_amount} {total_currency}"
                )

            flights.append(flight_info)

        # Tri par prix
        flights.sort(key=lambda f: f["price_amount"])

        return True, {
            "flights": flights,
            "count": len(flights),
            "origin": origin_code,
            "destination": dest_code,
            "date": departure_date,
            "return_date": return_date,
            "source": "duffel",
        }

    # =========================================================================
    # RESERVATION DE VOL
    # =========================================================================

    async def book_flight(
        self,
        offer_id: str,
        passengers: List[Dict],
        payment_type: str = "balance",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reserve un vol.

        Args:
            offer_id: ID de l'offre Duffel
            passengers: Liste de dicts avec:
                - given_name, family_name, born_on (YYYY-MM-DD),
                - email, phone_number, gender (m/f)
            payment_type: "balance" (Duffel balance) ou "arc_bsp_cash"

        Returns:
            (True, {"order": {...}}) ou (False, {"error": "..."})
        """
        settings = get_settings()
        if settings.foundation_test_mode:
            logger.warning("[BLOCKED] book_flight() disabled in foundation test mode")
            return False, {"error": "Confirmations desactivees en mode test fondateur", "blocked": True}

        if not self.is_configured:
            return False, {"error": "Duffel non configure."}

        # Valider l'offre (prix a jour)
        payload = {
            "data": {
                "selected_offers": [offer_id],
                "passengers": passengers,
                "type": "instant",
                "payments": [
                    {
                        "type": payment_type,
                        "amount": "0",  # sera rempli par Duffel
                        "currency": "EUR",
                    }
                ],
            }
        }

        result = await self._api_request("POST", "/air/orders", payload)
        if not result:
            return False, {"error": "Echec de la reservation. Verifie les informations et reessaie."}

        order = result.get("data", {})
        booking_ref = order.get("booking_reference", "")
        order_id = order.get("id", "")
        total = order.get("total_amount", "0")
        currency = order.get("total_currency", "EUR")

        slices = order.get("slices", [])
        route = ""
        if slices:
            first_seg = slices[0].get("segments", [{}])[0]
            _orig = first_seg.get("origin") or {}
            _last_seg = slices[0].get("segments", [{}])[-1]
            _dest = (_last_seg.get("destination") or {})
            origin = _orig.get("iata_code", "")
            dest = _dest.get("iata_code", "")
            dep_date = first_seg.get("departing_at", "").split("T")[0]
            route = f"{origin} → {dest} le {dep_date}"

        return True, {
            "order_id": order_id,
            "booking_reference": booking_ref,
            "total": f"{total} {currency}",
            "route": route,
            "status": "confirmed",
            "message": f"Reservation confirmee ! Ref: {booking_ref}. {route} pour {total} {currency}.",
        }

    # =========================================================================
    # RECHERCHE D'HOTELS (Stays API)
    # =========================================================================

    async def search_hotels(
        self,
        city: str,
        check_in: str,
        check_out: str,
        guests: int = 1,
        rooms: int = 1,
        max_results: int = 8,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recherche d'hotels via Duffel Stays.

        Returns:
            (True, {"hotels": [...]}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "Duffel non configure."}

        payload = {
            "data": {
                "rooms": rooms,
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guests": [{"type": "adult"} for _ in range(guests)],
                "location": {
                    "radius": 10,
                    "geographic_coordinates": await self._geocode_city(city),
                },
            }
        }

        # Verifier que le geocoding a marche
        coords = payload["data"]["location"]["geographic_coordinates"]
        if not coords.get("latitude"):
            # Fallback: recherche par nom
            return False, {"error": f"Impossible de localiser {city} pour la recherche d'hotels."}

        result = await self._api_request("POST", "/stays/search", payload)
        if not result:
            return False, {"error": "Impossible de rechercher les hotels. Reessaie."}

        results = (result.get("data") or {}).get("results", [])
        if not results:
            return True, {
                "hotels": [],
                "message": f"Aucun hotel disponible a {city} du {check_in} au {check_out}.",
            }

        hotels = []
        for h in results[:max_results]:
            accommodation = h.get("accommodation") or {}
            cheapest = h.get("cheapest_rate_total_amount", "0")
            currency = h.get("cheapest_rate_currency", "EUR")
            _rating = accommodation.get("rating") or {}
            _location = accommodation.get("location") or {}
            _address = _location.get("address") or {}

            hotel_info = {
                "id": h.get("id", ""),
                "name": accommodation.get("name", "Hotel"),
                "stars": _rating.get("value", ""),
                "address": _address.get("line_one", ""),
                "city": city,
                "price_total": f"{cheapest} {currency}",
                "price_amount": float(cheapest) if cheapest else 0,
                "price_currency": currency,
                "photos": [p.get("url", "") for p in accommodation.get("photos", [])[:3]],
                "amenities": accommodation.get("amenities", [])[:8],
                "check_in": check_in,
                "check_out": check_out,
                "bookable": True,
            }

            nights = self._calc_nights(check_in, check_out)
            per_night = round(hotel_info["price_amount"] / max(nights, 1), 2)
            hotel_info["price_per_night"] = f"{per_night} {currency}"
            hotel_info["summary"] = (
                f"{hotel_info['name']}"
                f"{' ' + str(hotel_info['stars']) + ' etoiles' if hotel_info['stars'] else ''}"
                f" — {per_night} {currency}/nuit"
                f" (total: {cheapest} {currency} pour {nights} nuit{'s' if nights > 1 else ''})"
            )
            hotels.append(hotel_info)

        hotels.sort(key=lambda h: h["price_amount"])

        return True, {
            "hotels": hotels,
            "count": len(hotels),
            "city": city,
            "check_in": check_in,
            "check_out": check_out,
            "source": "duffel",
        }

    # =========================================================================
    # RESERVATION D'HOTEL
    # =========================================================================

    async def book_hotel(
        self,
        rate_id: str,
        guest_info: Dict,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reserve un hotel.

        Args:
            rate_id: ID du tarif Duffel
            guest_info: Dict avec given_name, family_name, email, phone_number

        Returns:
            (True, {"booking": {...}}) ou (False, {"error": "..."})
        """
        settings = get_settings()
        if settings.foundation_test_mode:
            logger.warning("[BLOCKED] book_hotel() disabled in foundation test mode")
            return False, {"error": "Confirmations desactivees en mode test fondateur", "blocked": True}

        if not self.is_configured:
            return False, {"error": "Duffel non configure."}

        payload = {
            "data": {
                "quote_id": rate_id,
                "guests": [guest_info],
                "email": guest_info.get("email", ""),
                "phone_number": guest_info.get("phone_number", ""),
            }
        }

        result = await self._api_request("POST", "/stays/bookings", payload)
        if not result:
            return False, {"error": "Echec de la reservation hotel. Verifie les infos et reessaie."}

        booking = result.get("data", {})
        return True, {
            "booking_id": booking.get("id", ""),
            "status": booking.get("status", "confirmed"),
            "confirmation_code": booking.get("confirmation_code", ""),
            "message": f"Hotel reserve ! Confirmation: {booking.get('confirmation_code', 'en cours')}.",
        }

    # =========================================================================
    # UTILITAIRES
    # =========================================================================

    async def _geocode_city(self, city: str) -> Dict:
        """Geocode une ville via Open-Meteo (gratuit)."""
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(
                    f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=fr"
                )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return {
                        "latitude": results[0]["latitude"],
                        "longitude": results[0]["longitude"],
                    }
        except Exception as e:
            logger.warning(f"Geocode error for {city}: {e}")
        return {"latitude": 0, "longitude": 0}

    @staticmethod
    def _calc_nights(check_in: str, check_out: str) -> int:
        """Calcule le nombre de nuits entre deux dates."""
        try:
            from datetime import datetime
            d1 = datetime.strptime(check_in, "%Y-%m-%d")
            d2 = datetime.strptime(check_out, "%Y-%m-%d")
            return max((d2 - d1).days, 1)
        except Exception:
            return 1

    async def get_airlines(self) -> List[Dict]:
        """Liste les compagnies aeriennes disponibles."""
        result = await self._api_request("GET", "/air/airlines?limit=200")
        if not result:
            return []
        return [
            {"name": a.get("name", ""), "iata_code": a.get("iata_code", "")}
            for a in result.get("data", [])
            if a.get("iata_code")
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "mode": "test" if self.is_test else "live",
        }
