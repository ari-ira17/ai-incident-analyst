"""
map_utils.py
────────────
Модуль для работы с интерактивной картой Омска:
- Поиск координат улицы в streets.json
- Построение folium-карты с вспышками инцидентов
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

import folium
from folium import plugins

# ─── Пути к файлам ───────────────────────────────────────────────────────────
GEOJSON_PATH = Path(__file__).resolve().parent.parent / "omsk_districts.geojson"
STREETS_PATH = Path(__file__).resolve().parent.parent / "streets.json"

# ─── Центр Омска для карты ───────────────────────────────────────────────────
OMSK_CENTER = [54.9893, 73.3682]

# ─── Цвета районов ───────────────────────────────────────────────────────────
DISTRICT_COLORS = {
    "Кировский": "#e74c3c",
    "Ленинский": "#3498db",
    "Октябрьский": "#2ecc71",
    "Советский": "#f39c12",
    "Центральный": "#9b59b6",
}

# ─── Кэш для streets.json ────────────────────────────────────────────────────
_streets_cache: Optional[dict] = None


def load_streets_mapping() -> dict:
    """Загружает streets.json со структурой { 'ул. Название': { 'district': ..., 'lat': ..., 'lon': ... } }"""
    global _streets_cache
    if _streets_cache is not None:
        return _streets_cache
    if not STREETS_PATH.exists():
        _streets_cache = {}
        return _streets_cache
    with open(STREETS_PATH, "r", encoding="utf-8") as f:
        _streets_cache = json.load(f)
    return _streets_cache


def load_districts_geojson() -> dict:
    """Загружает GeoJSON с границами районов"""
    if not GEOJSON_PATH.exists():
        return {"type": "FeatureCollection", "features": []}
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def find_street_coords(address: str, streets: dict) -> Optional[dict]:
    """
    Ищет улицу в streets.json по адресу.
    Возвращает { 'district': ..., 'lat': ..., 'lon': ... } или None.

    Сначала точное совпадение, потом частичное (если адрес содержит название улицы).
    """
    if not address or not isinstance(address, str):
        return None

    addr_lower = address.lower().strip()

    # 1. Точное совпадение
    if address in streets:
        return streets[address]

    # 2. Поиск по ключам: нормализуем ключи и ищем вхождение
    for street_key, info in streets.items():
        key_lower = street_key.lower().strip()
        # Убираем "ул. ", "пр. " и т.п. для сравнения
        key_normalized = re.sub(r"^(ул|пр|пер|б-р|пл|ш|пр-д|туп)\.?\s*", "", key_lower).strip()
        addr_normalized = re.sub(r"^(ул|пр|пер|б-р|пл|ш|пр-д|туп)\.?\s*", "", addr_lower).strip()

        # Убираем номер дома из адреса для сравнения
        addr_clean = re.sub(r",\s*д\.?\s*\S*", "", addr_normalized)
        addr_clean = re.sub(r"\s+д\.?\s*\S*$", "", addr_clean)
        addr_clean = re.sub(r",\s*\d+.*$", "", addr_clean)
        addr_clean = re.sub(r"\s+\d+.*$", "", addr_clean)

        if key_normalized == addr_clean or key_normalized in addr_clean or addr_clean in key_normalized:
            return info

    return None


def severity_to_radius(severity: int) -> int:
    """Размер кружка в пикселях от severity (1-5)"""
    return {1: 6, 2: 10, 3: 16, 4: 24, 5: 35}.get(severity, 8)


def severity_to_opacity(severity: int) -> float:
    """Прозрачность от severity"""
    return {1: 0.4, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.85}.get(severity, 0.5)


def severity_to_color(severity: int) -> str:
    """Цвет кружка от severity"""
    return {1: "#2ecc71", 2: "#f39c12", 3: "#e67e22", 4: "#e74c3c", 5: "#c0392b"}.get(severity, "#666666")


def build_incident_map(
    incidents_df,
    streets_mapping: dict,
    district_filter: Optional[str] = None,
    min_severity: int = 1,
) -> folium.Map:
    """
    Строит интерактивную карту Омска с инцидентами.

    Параметры:
        incidents_df — polars/pandas DataFrame с колонками:
            - 'Улица' (адрес)
            - 'Тема' (категория)
            - 'severity' (ранг 1-5)
            - 'is_problem' (0/1)
            - 'Текст инцидента' (описание)
        streets_mapping — словарь из streets.json
        district_filter — если задан, показать только этот район
        min_severity — минимальный уровень severity

    Возвращает:
        folium.Map объект
    """
    # Конвертируем polars → pandas
    if hasattr(incidents_df, "to_pandas"):
        df = incidents_df.to_pandas()
    else:
        df = incidents_df.copy()

    # Создаём карту
    m = folium.Map(
        location=OMSK_CENTER,
        zoom_start=12,
        tiles="cartodbpositron",
        control_scale=True,
    )

    # ─── 1. Границы районов ──────────────────────────────────────────────
    geojson_data = load_districts_geojson()

    def style_function(feature):
        name = feature["properties"].get("short_name", "")
        color = DISTRICT_COLORS.get(name, "#666")
        return {"fillColor": color, "color": "#333", "weight": 2, "fillOpacity": 0.08, "dashArray": "5,5"}

    def highlight_function(feature):
        name = feature["properties"].get("short_name", "")
        color = DISTRICT_COLORS.get(name, "#666")
        return {"fillColor": color, "color": "#333", "weight": 3, "fillOpacity": 0.25}

    folium.GeoJson(
        geojson_data,
        name="Районы Омска",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Район:"], localize=True, sticky=True),
    ).add_to(m)

    # ─── 2. Инциденты ────────────────────────────────────────────────────
    if "is_problem" in df.columns:
        df_incidents = df[df["is_problem"] == 1].copy()
    else:
        df_incidents = df.copy()

    if "severity" in df_incidents.columns:
        df_incidents = df_incidents[df_incidents["severity"] >= min_severity]

    if df_incidents.empty:
        # Добавляем информационную метку в центр
        folium.Marker(
            location=OMSK_CENTER,
            icon=folium.DivIcon(html='<div style="font-size:16px;font-weight:bold;color:#666;">Нет данных</div>'),
        ).add_to(m)
        plugins.Fullscreen().add_to(m)
        folium.LayerControl().add_to(m)
        return m

    # Собираем точки с реальными координатами
    points = []
    not_found = 0
    for _, row in df_incidents.iterrows():
        address = str(row.get("Улица", ""))
        coords_info = find_street_coords(address, streets_mapping)

        if coords_info is None:
            not_found += 1
            continue

        district = coords_info["district"]
        lat = coords_info["lat"]
        lon = coords_info["lon"]

        # Применяем фильтр района
        if district_filter and district != district_filter:
            continue

        severity = int(row.get("severity", 1))
        topic = str(row.get("Тема", "Не указана"))
        text = str(row.get("Текст инцидента", ""))[:200]

        points.append({
            "lat": lat,
            "lon": lon,
            "severity": severity,
            "topic": topic,
            "text": text,
            "address": address,
            "district": district,
        })

    # Добавляем маркеры
    for p in points:
        radius = severity_to_radius(p["severity"])
        opacity = severity_to_opacity(p["severity"])
        color = severity_to_color(p["severity"])

        popup_html = f"""
        <div style="font-family:Segoe UI,sans-serif;font-size:13px;min-width:220px;">
            <b>📍 {p['district']}</b><br>
            <b>Адрес:</b> {p['address']}<br>
            <b>Тема:</b> {p['topic']}<br>
            <b>Опасность:</b> {'🔥' * p['severity']} ({p['severity']}/5)<br>
            <hr style="margin:4px 0;">
            <i>{p['text']}</i>
        </div>
        """

        # Для severity 4-5 — пульсирующий эффект (большой полупрозрачный + основной)
        if p["severity"] >= 4:
            folium.CircleMarker(
                location=[p["lat"], p["lon"]],
                radius=radius * 1.8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=opacity * 0.25,
                weight=1,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(m)

        # Основной маркер
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=radius,
            color="#ffffff",
            weight=1.5,
            fill=True,
            fillColor=color,
            fillOpacity=opacity,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{p['topic']} — {p['severity']}/5",
        ).add_to(m)

    # ─── 3. Легенда ──────────────────────────────────────────────────────
    legend_html = """
    <div style="
        position: fixed; bottom: 20px; right: 20px; z-index: 1000;
        background: white; padding: 12px; border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        font-family: 'Segoe UI', sans-serif; font-size: 13px; min-width: 160px;
    ">
        <b>🔥 Уровень опасности</b><br>
        <span style="color:#2ecc71;">●</span> 1 — Низкий<br>
        <span style="color:#f39c12;">●</span> 2 — Умеренный<br>
        <span style="color:#e67e22;">●</span> 3 — Средний<br>
        <span style="color:#e74c3c;">●</span> 4 — Высокий<br>
        <span style="color:#c0392b;">●</span> 5 — Критический 🔥<br>
        <hr style="margin:6px 0;">
        <b>🏘️ Районы</b><br>
        <span style="color:#e74c3c;">■</span> Кировский<br>
        <span style="color:#3498db;">■</span> Ленинский<br>
        <span style="color:#2ecc71;">■</span> Октябрьский<br>
        <span style="color:#f39c12;">■</span> Советский<br>
        <span style="color:#9b59b6;">■</span> Центральный<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    plugins.Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)

    return m


def get_district_stats(incidents_df, streets_mapping: dict) -> dict:
    """Статистика по районам: количество, severity, топ-проблемы"""
    if hasattr(incidents_df, "to_pandas"):
        df = incidents_df.to_pandas()
    else:
        df = incidents_df.copy()

    if "is_problem" in df.columns:
        df = df[df["is_problem"] == 1]

    stats = {d: {"count": 0, "total_severity": 0, "avg_severity": 0, "topics": {}, "color": c}
             for d, c in DISTRICT_COLORS.items()}

    for _, row in df.iterrows():
        address = str(row.get("Улица", ""))
        coords_info = find_street_coords(address, streets_mapping)
        if coords_info is None:
            continue
        district = coords_info["district"]
        severity = int(row.get("severity", 0))
        topic = str(row.get("Тема", "Не указана"))

        if district in stats:
            stats[district]["count"] += 1
            stats[district]["total_severity"] += severity
            stats[district]["topics"][topic] = stats[district]["topics"].get(topic, 0) + 1

    for d in stats:
        if stats[d]["count"] > 0:
            stats[d]["avg_severity"] = round(stats[d]["total_severity"] / stats[d]["count"], 2)
        stats[d]["topics"] = dict(sorted(stats[d]["topics"].items(), key=lambda x: -x[1]))

    return stats