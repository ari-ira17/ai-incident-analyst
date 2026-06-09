"""
src/map_utils/geocoder.py
─────────────────────────
Геокодинг улиц Омска через Nominatim (OpenStreetMap).
Бесплатно, без API-ключа. Ограничение: ~1 запрос/сек.

Координаты → Nominatim API (с кэшированием).
Район → streets.json (там он точный для всех улиц Омска).
Если улицы нет в streets.json — район извлекается из ответа Nominatim.
"""

import json
import os
import time
import hashlib
from typing import Optional

import requests


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

STREETS_PATH = os.path.join(_PROJECT_ROOT, "streets.json")
CACHE_PATH = os.path.join(
    _PROJECT_ROOT,
    "data", "reference", "geocode_cache.json",
)


_streets_cache: Optional[dict] = None


def _load_streets_district(street_name: str) -> str:
    """Ищет улицу в streets.json и возвращает район (нечёткое совпадение)."""
    global _streets_cache
    if _streets_cache is None:
        if not os.path.exists(STREETS_PATH):
            _streets_cache = {}
        else:
            with open(STREETS_PATH, encoding="utf-8") as f:
                _streets_cache = json.load(f)

    if not _streets_cache:
        return ""

    if street_name in _streets_cache:
        return _streets_cache[street_name].get("district", "")

    street_lower = street_name.lower().strip()
    for key, info in _streets_cache.items():
        if key.lower() == street_lower:
            return info.get("district", "")

    for key, info in _streets_cache.items():
        key_lower = key.lower()
        if street_lower in key_lower or key_lower in street_lower:
            return info.get("district", "")

    return ""


_geocode_cache: Optional[dict] = None


def _load_geocode_cache() -> dict:
    """Загружает кэш геокодинга с диска."""
    global _geocode_cache
    if _geocode_cache is not None:
        return _geocode_cache
    if not os.path.exists(CACHE_PATH):
        _geocode_cache = {}
        return _geocode_cache
    with open(CACHE_PATH, encoding="utf-8") as f:
        _geocode_cache = json.load(f)
    return _geocode_cache


def _save_geocode_cache():
    """Сохраняет кэш геокодинга на диск."""
    global _geocode_cache
    if _geocode_cache is None:
        return
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(_geocode_cache, f, ensure_ascii=False, indent=2)



OMSK_DISTRICTS = [
    "Кировский",
    "Ленинский",
    "Октябрьский",
    "Советский",
    "Центральный",
]


DISTRICT_ALIASES = {
    "кировский": "Кировский",
    "кировский административный округ": "Кировский",
    "кировский округ": "Кировский",
    "ленинский": "Ленинский",
    "ленинский административный округ": "Ленинский",
    "ленинский округ": "Ленинский",
    "октябрьский": "Октябрьский",
    "октябрьский административный округ": "Октябрьский",
    "октябрьский округ": "Октябрьский",
    "советский": "Советский",
    "советский административный округ": "Советский",
    "советский округ": "Советский",
    "центральный": "Центральный",
    "центральный административный округ": "Центральный",
    "центральный округ": "Центральный",
}


def _extract_district_from_address(address: str) -> str:
    """
    Извлекает район Омска из строки адреса Nominatim.
    Ищет названия районов в адресе.
    """
    if not address:
        return ""
    address_lower = address.lower()

 
    for alias, canonical in DISTRICT_ALIASES.items():
        if alias in address_lower:
            return canonical

    for district in OMSK_DISTRICTS:
        if district.lower() in address_lower:
            return district

    return ""



NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "AIIncidentAnalyst/1.0 (omsk-incident-map)"


def _nominatim_request(query: str) -> Optional[dict]:
    """
    Выполняет запрос к Nominatim с addressdetails=1,
    чтобы получить полный адрес и извлечь район.
    Возвращает {lat, lon, display_name, address} или None.
    """
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and len(data) > 0:
            return {
                "lat": float(data[0]["lat"]),
                "lon": float(data[0]["lon"]),
                "display_name": data[0].get("display_name", ""),
                "address": data[0].get("address", {}),
            }
    except requests.RequestException as e:
        print(f"[geocoder] Nominatim error for '{query}': {e}")
    return None


def geocode_street(street_name: str, city: str = "Омск") -> Optional[dict]:
    """
    Возвращает координаты улицы {lat, lon, district, source}.

    Район: сначала streets.json (точный), если нет — из ответа Nominatim.
    Координаты: Nominatim API (с кэшированием).
    source = 'cache' | 'nominatim'
    """
    if not street_name or street_name == "Не известно":
        return None

    cache_key = hashlib.md5(street_name.lower().encode()).hexdigest()

    cache = _load_geocode_cache()
    if cache_key in cache:
        entry = cache[cache_key]
        return {
            "lat": entry["lat"],
            "lon": entry["lon"],
            "district": entry.get("district", ""),
            "source": "cache",
        }

    district = _load_streets_district(street_name)

    query = f"{city}, {street_name}"
    result = _nominatim_request(query)

    if result is None:
        result = _nominatim_request(street_name)

    if result:
        if not district:
            address = result.get("address", {})
            district = (
                address.get("city_district", "")
                or address.get("suburb", "")
                or address.get("county", "")
            )
            district = _extract_district_from_address(district) or _extract_district_from_address(
                result.get("display_name", "")
            )

        entry = {
            "lat": result["lat"],
            "lon": result["lon"],
            "district": district,
        }
        cache[cache_key] = entry
        _save_geocode_cache()

        time.sleep(1.1)

        return {
            "lat": entry["lat"],
            "lon": entry["lon"],
            "district": district,
            "source": "nominatim",
        }

    return None

def batch_geocode_streets(
    street_names: list[str],
    city: str = "Омск",
    max_requests: int = 50,
) -> dict:
    """
    Массово геокодирует список улиц через Nominatim.
    Возвращает словарь {улица: {lat, lon, district}} для успешно найденных.
    max_requests — ограничение на количество запросов за вызов.
    """
    results = {}
    count = 0
    for name in street_names:
        if count >= max_requests:
            print(f"[geocoder] Достигнут лимит в {max_requests} запросов.")
            break
        coords = geocode_street(name, city=city)
        if coords:
            results[name] = {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "district": coords.get("district", ""),
            }
            count += 1
            print(f"[geocoder] {count}/{max_requests}: {name} -> {coords['lat']}, {coords['lon']} | {coords.get('district', '?')}")
    return results
