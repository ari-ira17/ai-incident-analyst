"""
src/map_utils/map_utils.py
──────────────────────────
Утилиты для построения интерактивной карты инцидентов Омска.

Координаты улиц и район определяются через Nominatim API (src/map_utils/geocoder.py).
Результаты кэшируются, повторные запросы не выполняются.
"""

import json
import os
import polars as pl
import folium
from folium.plugins import HeatMap
from typing import Optional

GEOJSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "omsk_districts.geojson")

DISTRICT_COLORS = {
    "Центральный": "#9b59b6",
    "Советский": "#f39c12",
    "Кировский": "#e74c3c",
    "Ленинский": "#3498db",
    "Октябрьский": "#2ecc71",
}

SEVERITY_COLORS = {1: "#27ae60", 2: "#f1c40f", 3: "#e67e22", 4: "#e74c3c", 5: "#c0392b"}


def load_streets_mapping() -> dict:
    """Заглушка для обратной совместимости. Координаты теперь через API."""
    return {}


def get_street_coordinates(
    raw_street: str,
    streets_mapping: dict = None,
    use_geocoder: bool = True,
) -> Optional[dict]:
    """
    Возвращает координаты улицы {lat, lon, district, source}.
    Всё через Nominatim API (с кэшированием).
    """
    if not raw_street or raw_street == "Не известно":
        return None

    if not use_geocoder:
        return None

    try:
        from src.map_utils.geocoder import geocode_street
        result = geocode_street(raw_street)
        if result is not None:
            return result
    except Exception as e:
        print(f"[map_utils] Ошибка геокодинга для '{raw_street}': {e}")

    return None


def _load_geojson() -> Optional[dict]:
    """Загружает omsk_districts.geojson."""
    if not os.path.exists(GEOJSON_PATH):
        return None
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def _add_district_polygons(m: folium.Map):
    """Добавляет стилизованные полигоны районов на карту."""
    geojson_data = _load_geojson()
    if geojson_data is None:
        return

    district_centers = {
        "Кировский": [54.960, 73.310],
        "Ленинский": [54.920, 73.350],
        "Октябрьский": [54.970, 73.440],
        "Советский": [55.040, 73.400],
        "Центральный": [54.960, 73.420],
    }

    folium.GeoJson(
        geojson_data,
        name="Районы Омска",
        style_function=lambda x: {
            "fillColor": x["properties"].get("color", "#gray"),
            "color": "#333333",
            "weight": 2,
            "fillOpacity": 0.10,
        },
        highlight_function=lambda x: {"fillOpacity": 0.25, "weight": 3},
        tooltip=folium.GeoJsonTooltip(
            fields=["name", "description"],
            aliases=["Район:", "Описание:"],
            style="font-size: 13px;",
        ),
    ).add_to(m)

    for name, coords in district_centers.items():
        color = DISTRICT_COLORS.get(name, "#333333")
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f'<div style="font-size: 14px; font-weight: bold; color: {color}; '
                     f'background: rgba(255,255,255,0.85); padding: 3px 8px; '
                     f'border-radius: 4px; border: 2px solid {color};">{name}</div>'
            ),
        ).add_to(m)


def build_incident_map(
    incidents_df: pl.DataFrame,
    streets_mapping: dict = None,
    district_filter: Optional[str] = None,
    min_severity: int = 1,
    use_geocoder: bool = True,
) -> folium.Map:
    """Строит карту Omsk с инцидентами.

    Координаты и район определяются через Nominatim API.
    Фильтрация по району происходит по district из ответа API.

    Параметры:
        streets_mapping: не используется (оставлен для совместимости)
        use_geocoder: если True, координаты запрашиваются через Nominatim API
    """
    m = folium.Map(location=[54.989, 73.368], zoom_start=12, tiles="OpenStreetMap")

    _add_district_polygons(m)

    if incidents_df.is_empty():
        return m

    df = incidents_df.filter(pl.col("severity") >= min_severity)

    if df.is_empty():
        return m

    points = []
    for row in df.iter_rows(named=True):
        raw_street = str(row.get("Улица", "") or "")
        coords = get_street_coordinates(raw_street, use_geocoder=use_geocoder)
        if coords is None:
            continue

        lat, lon = coords["lat"], coords["lon"]
        severity = int(row.get("severity", 1))
        severity = max(1, min(5, severity))
        topic = str(row.get("Тема", "") or "")
        text = str(row.get("Текст инцидента", "") or "")
        district = coords.get("district", "Неизвестно")
        source = coords.get("source", "nominatim")

        if district_filter and district != district_filter:
            continue

        radius = 4 + severity * 3
        color = SEVERITY_COLORS.get(severity, "#27ae60")

        source_label = {"nominatim": "🌐", "cache": "💾"}.get(source, "❓")

        popup_text = f"""
        <b>Улица:</b> {raw_street}<br>
        <b>Район:</b> {district}<br>
        <b>Тема:</b> {topic}<br>
        <b>Опасность:</b> {severity}/5<br>
        <b>Координаты:</b> {source_label} {source}<br>
        <b>Текст:</b> {text[:200]}{'...' if len(text) > 200 else ''}
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=0.6,
            popup=folium.Popup(popup_text, max_width=350),
            tooltip=f"{raw_street} | Опасность: {severity}",
        ).add_to(m)

        points.append([lat, lon, severity])

    if points:
        HeatMap(
            data=[[p[0], p[1], p[2]] for p in points],
            name="Тепловая карта",
            min_opacity=0.3,
            max_zoom=14,
            radius=20,
            blur=15,
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def get_district_stats(df: pl.DataFrame, streets_mapping: dict = None, use_geocoder: bool = True) -> dict:
    """Собирает статистику по районам на основе улиц (через API)."""
    stats = {d: {"count": 0, "severities": [], "topics": {}} for d in DISTRICT_COLORS}
    for d in DISTRICT_COLORS:
        stats[d]["color"] = DISTRICT_COLORS[d]

    for row in df.iter_rows(named=True):
        raw_street = str(row.get("Улица", "") or "")
        coords = get_street_coordinates(raw_street, use_geocoder=use_geocoder)
        if coords is None:
            continue
        district = coords.get("district", "Неизвестно")
        if district not in stats:
            continue

        stats[district]["count"] += 1
        stats[district]["severities"].append(int(row.get("severity", 1)))

        topic = str(row.get("Тема", "") or "Без темы")
        stats[district]["topics"][topic] = stats[district]["topics"].get(topic, 0) + 1

    for d in stats:
        sevs = stats[d]["severities"]
        stats[d]["avg_severity"] = round(sum(sevs) / len(sevs), 1) if sevs else 0
        stats[d]["topics"] = dict(
            sorted(stats[d]["topics"].items(), key=lambda x: -x[1])
        )
        del stats[d]["severities"]

    return stats
