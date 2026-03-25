"""
Amadeus API Client - Vols et Hotels

Utilise l'API Amadeus for Developers (self-service).
L'exploitant cree un compte sur developers.amadeus.com et obtient ses cles.

Env vars:
    AMADEUS_API_KEY     - API Key (client_id)
    AMADEUS_API_SECRET  - API Secret (client_secret)
    AMADEUS_ENV         - "test" ou "production" (default: test)

Usage:
    client = AmadeusClient.from_env()
    flights = await client.search_flights("PAR", "LYS", "2026-04-15")
    hotels = await client.search_hotels("PAR", "2026-04-15", "2026-04-17")
"""
import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

BASE_URLS = {
    "test": "https://test.api.amadeus.com",
    "production": "https://api.amadeus.com",
}

# Codes IATA des villes francaises courantes
CITY_CODES = {
    "paris": "PAR", "lyon": "LYS", "marseille": "MRS", "toulouse": "TLS",
    "nice": "NCE", "nantes": "NTE", "strasbourg": "SXB", "montpellier": "MPL",
    "bordeaux": "BOD", "lille": "LIL", "rennes": "RNS", "grenoble": "GNB",
    "toulon": "TLN", "dijon": "DIJ", "clermont-ferrand": "CFE", "metz": "ETZ",
    "nancy": "ETZ", "perpignan": "PGF", "pau": "PUF", "biarritz": "BIQ",
    "ajaccio": "AJA", "bastia": "BIA", "la reunion": "RUN",
    "londres": "LON", "london": "LON", "bruxelles": "BRU", "amsterdam": "AMS",
    "rome": "ROM", "milan": "MIL", "barcelone": "BCN", "madrid": "MAD",
    "lisbonne": "LIS", "berlin": "BER", "new york": "NYC", "montreal": "YMQ",
    "marrakech": "RAK", "tunis": "TUN", "alger": "ALG", "dakar": "DSS",
}

# Gares SNCF -> code IATA rail (pour trains)
TRAIN_STATIONS = {
    "paris": "FRPAR", "lyon": "FRLYS", "marseille": "FRMRS",
    "bordeaux": "FRBOD", "lille": "FRLIL", "strasbourg": "FRSXB",
    "nantes": "FRNTE", "toulouse": "FRTLS", "nice": "FRNCE",
    "montpellier": "FRMPL", "rennes": "FRRNS",
}


class AmadeusClient:
    def __init__(self, api_key: str, api_secret: str, env: str = "test"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = BASE_URLS.get(env, BASE_URLS["test"])
        self._token: Optional[str] = None
        self._token_expires: float = 0

    @classmethod
    def from_env(cls) -> "AmadeusClient":
        api_key = os.getenv("AMADEUS_API_KEY", "")
        api_secret = os.getenv("AMADEUS_API_SECRET", "")
        env = os.getenv("AMADEUS_ENV", "test")
        if not api_key:
            logger.info("AMADEUS_API_KEY non configuree — reservations vols/hotels desactivees")
        return cls(api_key=api_key, api_secret=api_secret, env=env)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    async def _get_token(self) -> Optional[str]:
        """Obtient un token OAuth2 (cache 25min)."""
        if self._token and time.time() < self._token_expires:
            return self._token

        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(
                    f"{self.base_url}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.api_key,
                        "client_secret": self.api_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            if resp.status_code == 200:
                data = resp.json()
                self._token = data["access_token"]
                self._token_expires = time.time() + data.get("expires_in", 1799) - 60
                return self._token
            else:
                logger.error(f"Amadeus auth failed: {resp.status_code} {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Amadeus auth error: {e}")
            return None

    async def _api_get(self, path: str, params: Dict) -> Optional[Dict]:
        """GET authentifie sur l'API Amadeus."""
        token = await self._get_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as http:
                resp = await http.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning(f"Amadeus GET {path} → {resp.status_code}: {resp.text[:300]}")
                return None
        except Exception as e:
            logger.error(f"Amadeus API error: {e}")
            return None

    # =========================================================================
    # VOLS
    # =========================================================================

    def resolve_city_code(self, city_name: str) -> str:
        """Resout un nom de ville en code IATA."""
        normalized = city_name.lower().strip()
        if normalized in CITY_CODES:
            return CITY_CODES[normalized]
        # Si c'est deja un code IATA (3 lettres majuscules)
        if len(city_name) == 3 and city_name.isalpha():
            return city_name.upper()
        return normalized.upper()[:3]

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 5,
        travel_class: str = "ECONOMY",
        nonstop: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recherche de vols.

        Args:
            origin: Ville ou code IATA de depart (ex: "Paris" ou "PAR")
            destination: Ville ou code IATA d'arrivee
            departure_date: Date YYYY-MM-DD
            return_date: Date retour (optionnel, aller simple si absent)
            adults: Nombre de passagers adultes
            max_results: Nombre max de resultats
            travel_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
            nonstop: True pour vols directs uniquement

        Returns:
            (True, {"flights": [...]}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "Amadeus non configure. L'exploitant doit ajouter AMADEUS_API_KEY et AMADEUS_API_SECRET."}

        origin_code = self.resolve_city_code(origin)
        dest_code = self.resolve_city_code(destination)

        params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest_code,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "travelClass": travel_class,
            "currencyCode": "EUR",
        }
        if return_date:
            params["returnDate"] = return_date
        if nonstop:
            params["nonStop"] = "true"

        data = await self._api_get("/v2/shopping/flight-offers", params)
        if not data:
            return False, {"error": "Impossible de rechercher les vols. Reessaie dans un moment."}

        offers = data.get("data", [])
        if not offers:
            return True, {"flights": [], "message": f"Aucun vol trouve de {origin} vers {destination} le {departure_date}."}

        # Formatter les resultats
        flights = []
        for offer in offers[:max_results]:
            price = offer.get("price", {})
            itineraries = offer.get("itineraries", [])

            flight_info = {
                "id": offer.get("id"),
                "price": f"{price.get('total', '?')} {price.get('currency', 'EUR')}",
                "price_cents": int(float(price.get("total", 0)) * 100),
                "airline": "",
                "segments": [],
            }

            for itin in itineraries:
                segments = itin.get("segments", [])
                for seg in segments:
                    flight_info["airline"] = flight_info["airline"] or seg.get("carrierCode", "")
                    flight_info["segments"].append({
                        "departure": seg.get("departure", {}).get("iataCode", ""),
                        "departure_time": seg.get("departure", {}).get("at", ""),
                        "arrival": seg.get("arrival", {}).get("iataCode", ""),
                        "arrival_time": seg.get("arrival", {}).get("at", ""),
                        "carrier": seg.get("carrierCode", ""),
                        "flight_number": f"{seg.get('carrierCode', '')}{seg.get('number', '')}",
                        "duration": seg.get("duration", ""),
                    })

            # Resume lisible
            if flight_info["segments"]:
                first = flight_info["segments"][0]
                last = flight_info["segments"][-1]
                dep_time = first["departure_time"].split("T")[1][:5] if "T" in first["departure_time"] else ""
                arr_time = last["arrival_time"].split("T")[1][:5] if "T" in last["arrival_time"] else ""
                stops = len(flight_info["segments"]) - 1
                stops_text = "direct" if stops == 0 else f"{stops} escale{'s' if stops > 1 else ''}"
                flight_info["summary"] = f"{first['departure']} {dep_time} → {last['arrival']} {arr_time} ({stops_text}) — {flight_info['price']}"

            flights.append(flight_info)

        return True, {
            "flights": flights,
            "count": len(flights),
            "origin": origin_code,
            "destination": dest_code,
            "date": departure_date,
        }

    # =========================================================================
    # HOTELS
    # =========================================================================

    async def search_hotels(
        self,
        city: str,
        check_in: str,
        check_out: str,
        adults: int = 1,
        rooms: int = 1,
        max_results: int = 5,
        price_range: Optional[str] = None,
        stars: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Recherche d'hotels.

        Args:
            city: Ville ou code IATA
            check_in: Date d'arrivee YYYY-MM-DD
            check_out: Date de depart YYYY-MM-DD
            adults: Nombre d'adultes
            rooms: Nombre de chambres
            max_results: Nombre max
            price_range: Fourchette de prix (ex: "50-150")
            stars: Nombre d'etoiles minimum (1-5)

        Returns:
            (True, {"hotels": [...]}) ou (False, {"error": "..."})
        """
        if not self.is_configured:
            return False, {"error": "Amadeus non configure. L'exploitant doit ajouter AMADEUS_API_KEY et AMADEUS_API_SECRET."}

        city_code = self.resolve_city_code(city)

        # Etape 1: chercher les hotels dans la ville
        hotel_params = {
            "cityCode": city_code,
        }
        if stars:
            hotel_params["ratings"] = str(stars)

        hotels_data = await self._api_get("/v1/reference-data/locations/hotels/by-city", hotel_params)
        if not hotels_data or not hotels_data.get("data"):
            return True, {"hotels": [], "message": f"Aucun hotel trouve a {city}."}

        # Prendre les premiers hotel IDs
        hotel_ids = [h["hotelId"] for h in hotels_data["data"][:20]]

        # Etape 2: chercher les offres pour ces hotels
        offer_params = {
            "hotelIds": ",".join(hotel_ids[:20]),
            "checkInDate": check_in,
            "checkOutDate": check_out,
            "adults": adults,
            "roomQuantity": rooms,
            "currency": "EUR",
            "bestRateOnly": "true",
        }
        if price_range:
            parts = price_range.split("-")
            if len(parts) == 2:
                offer_params["priceRange"] = f"{parts[0]}-{parts[1]}"

        offers_data = await self._api_get("/v3/shopping/hotel-offers", offer_params)
        if not offers_data or not offers_data.get("data"):
            return True, {"hotels": [], "message": f"Pas de disponibilites a {city} du {check_in} au {check_out}."}

        hotels = []
        for hotel_offer in offers_data["data"][:max_results]:
            hotel = hotel_offer.get("hotel", {})
            offers = hotel_offer.get("offers", [])
            best_offer = offers[0] if offers else {}
            price = best_offer.get("price", {})

            hotel_info = {
                "id": hotel_offer.get("id", ""),
                "hotel_id": hotel.get("hotelId", ""),
                "name": hotel.get("name", "Hotel"),
                "stars": hotel.get("rating", ""),
                "city": city_code,
                "price_per_night": f"{price.get('total', '?')} {price.get('currency', 'EUR')}",
                "price_cents": int(float(price.get("total", 0)) * 100),
                "room_type": best_offer.get("room", {}).get("description", {}).get("text", ""),
                "cancellation": "flexible" if best_offer.get("policies", {}).get("cancellations") else "non remboursable",
                "check_in": check_in,
                "check_out": check_out,
            }
            hotel_info["summary"] = (
                f"{hotel_info['name']}"
                f"{' ' + str(hotel_info['stars']) + ' etoiles' if hotel_info['stars'] else ''}"
                f" — {hotel_info['price_per_night']}/nuit"
                f" ({hotel_info['cancellation']})"
            )
            hotels.append(hotel_info)

        return True, {
            "hotels": hotels,
            "count": len(hotels),
            "city": city_code,
            "check_in": check_in,
            "check_out": check_out,
        }

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "env": "production" if "api.amadeus.com" in self.base_url else "test",
        }
