from __future__ import annotations

from datetime import datetime

from app.storage.db import connect


def _null_stats() -> dict:
    return {
        "temp_min": None, "temp_max": None, "temp_avg": None,
        "hum_min": None,  "hum_max": None,  "hum_avg": None,
        "sample_count": 0,
    }


def _row_to_point(row: dict, label_key: str) -> dict:
    return {
        "label":    row[label_key],
        "temp":     round(row["avg_temp"], 1) if row["avg_temp"] is not None else None,
        "temp_min": round(row["min_temp"], 1) if row["min_temp"] is not None else None,
        "temp_max": round(row["max_temp"], 1) if row["max_temp"] is not None else None,
        "hum":      round(row["avg_hum"],  1) if row["avg_hum"]  is not None else None,
        "hum_min":  round(row["min_hum"],  1) if row["min_hum"]  is not None else None,
        "hum_max":  round(row["max_hum"],  1) if row["max_hum"]  is not None else None,
    }


async def get_env_daily(date_str: str) -> dict:
    """日視圖：5 分鐘槽平均值，date_str='YYYY-MM-DD'"""
    slot_expr = (
        "strftime('%Y-%m-%dT%H:', ts) || "
        "printf('%02d', (CAST(strftime('%M', ts) AS INTEGER) / 5) * 5)"
    )
    sql = f"""
        SELECT
            {slot_expr}  AS slot,
            AVG(temperature)           AS avg_temp,
            MIN(temperature)           AS min_temp,
            MAX(temperature)           AS max_temp,
            AVG(humidity)              AS avg_hum,
            MIN(humidity)              AS min_hum,
            MAX(humidity)              AS max_hum,
            COUNT(*)                   AS cnt
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
        GROUP BY {slot_expr}
        ORDER BY slot ASC
    """
    stats_sql = """
        SELECT
            MIN(temperature) AS temp_min, MAX(temperature) AS temp_max, AVG(temperature) AS temp_avg,
            MIN(humidity)    AS hum_min,  MAX(humidity)    AS hum_max,  AVG(humidity)    AS hum_avg,
            COUNT(*)         AS sample_count
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
    """
    prefix = date_str + "%"
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        rows = await (await db.execute(sql, (prefix,))).fetchall()
        stat_row = await (await db.execute(stats_sql, (prefix,))).fetchone()

    # slot = "YYYY-MM-DDTHH:MM"，取 [11:16] 得 "HH:MM"
    points = []
    for r in rows:
        p = _row_to_point(r, "slot")
        p["label"] = r["slot"][11:16]
        points.append(p)
    if stat_row and stat_row["sample_count"]:
        stats = {
            "temp_min": round(stat_row["temp_min"], 1),
            "temp_max": round(stat_row["temp_max"], 1),
            "temp_avg": round(stat_row["temp_avg"], 1),
            "hum_min":  round(stat_row["hum_min"],  1),
            "hum_max":  round(stat_row["hum_max"],  1),
            "hum_avg":  round(stat_row["hum_avg"],  1),
            "sample_count": stat_row["sample_count"],
        }
    else:
        stats = _null_stats()
    return {"scale": "day", "ref": date_str, "points": points, "stats": stats}


async def get_env_monthly(year_month: str) -> dict:
    """月視圖：每天聚合，year_month='YYYY-MM'"""
    sql = """
        SELECT
            strftime('%Y-%m-%d', ts) AS day,
            AVG(temperature)          AS avg_temp,
            MIN(temperature)          AS min_temp,
            MAX(temperature)          AS max_temp,
            AVG(humidity)             AS avg_hum,
            MIN(humidity)             AS min_hum,
            MAX(humidity)             AS max_hum,
            COUNT(*)                  AS cnt
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
        GROUP BY strftime('%Y-%m-%d', ts)
        ORDER BY day ASC
    """
    stats_sql = """
        SELECT
            MIN(temperature) AS temp_min, MAX(temperature) AS temp_max, AVG(temperature) AS temp_avg,
            MIN(humidity)    AS hum_min,  MAX(humidity)    AS hum_max,  AVG(humidity)    AS hum_avg,
            COUNT(*)         AS sample_count
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
    """
    prefix = year_month + "%"
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        rows = await (await db.execute(sql, (prefix,))).fetchall()
        stat_row = await (await db.execute(stats_sql, (prefix,))).fetchone()

    points = []
    for r in rows:
        p = _row_to_point(r, "day")
        p["label"] = r["day"][5:]  # MM-DD
        points.append(p)

    if stat_row and stat_row["sample_count"]:
        stats = {
            "temp_min": round(stat_row["temp_min"], 1),
            "temp_max": round(stat_row["temp_max"], 1),
            "temp_avg": round(stat_row["temp_avg"], 1),
            "hum_min":  round(stat_row["hum_min"],  1),
            "hum_max":  round(stat_row["hum_max"],  1),
            "hum_avg":  round(stat_row["hum_avg"],  1),
            "sample_count": stat_row["sample_count"],
        }
    else:
        stats = _null_stats()
    return {"scale": "month", "ref": year_month, "points": points, "stats": stats}


async def get_env_yearly(year: str) -> dict:
    """年視圖：每月聚合，year='YYYY'"""
    sql = """
        SELECT
            strftime('%Y-%m', ts) AS month,
            AVG(temperature)       AS avg_temp,
            MIN(temperature)       AS min_temp,
            MAX(temperature)       AS max_temp,
            AVG(humidity)          AS avg_hum,
            MIN(humidity)          AS min_hum,
            MAX(humidity)          AS max_hum,
            COUNT(*)               AS cnt
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
        GROUP BY strftime('%Y-%m', ts)
        ORDER BY month ASC
    """
    stats_sql = """
        SELECT
            MIN(temperature) AS temp_min, MAX(temperature) AS temp_max, AVG(temperature) AS temp_avg,
            MIN(humidity)    AS hum_min,  MAX(humidity)    AS hum_max,  AVG(humidity)    AS hum_avg,
            COUNT(*)         AS sample_count
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
    """
    prefix = year + "%"
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        rows = await (await db.execute(sql, (prefix,))).fetchall()
        stat_row = await (await db.execute(stats_sql, (prefix,))).fetchone()

    points = []
    for r in rows:
        p = _row_to_point(r, "month")
        p["label"] = r["month"][5:]  # MM
        points.append(p)

    if stat_row and stat_row["sample_count"]:
        stats = {
            "temp_min": round(stat_row["temp_min"], 1),
            "temp_max": round(stat_row["temp_max"], 1),
            "temp_avg": round(stat_row["temp_avg"], 1),
            "hum_min":  round(stat_row["hum_min"],  1),
            "hum_max":  round(stat_row["hum_max"],  1),
            "hum_avg":  round(stat_row["hum_avg"],  1),
            "sample_count": stat_row["sample_count"],
        }
    else:
        stats = _null_stats()
    return {"scale": "year", "ref": year, "points": points, "stats": stats}


async def get_env_today_extremes() -> dict:
    """今日 min/max/avg，給 stat cards 用"""
    today = datetime.now().date().isoformat()
    sql = """
        SELECT
            MIN(temperature) AS temp_min, MAX(temperature) AS temp_max, AVG(temperature) AS temp_avg,
            MIN(humidity)    AS hum_min,  MAX(humidity)    AS hum_max,  AVG(humidity)    AS hum_avg,
            COUNT(*)         AS sample_count
        FROM indoor_env_logs
        WHERE ts LIKE ?
          AND temperature IS NOT NULL
          AND humidity    IS NOT NULL
    """
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        row = await (await db.execute(sql, (today + "%",))).fetchone()

    if row and row["sample_count"]:
        return {
            "temp_min": round(row["temp_min"], 1),
            "temp_max": round(row["temp_max"], 1),
            "temp_avg": round(row["temp_avg"], 1),
            "hum_min":  round(row["hum_min"],  1),
            "hum_max":  round(row["hum_max"],  1),
            "hum_avg":  round(row["hum_avg"],  1),
            "sample_count": row["sample_count"],
        }
    return _null_stats()


async def get_available_years() -> list[str]:
    """資料庫中有資料的年份清單（降序）"""
    sql = """
        SELECT DISTINCT strftime('%Y', ts) AS year
        FROM indoor_env_logs
        WHERE temperature IS NOT NULL
          AND humidity IS NOT NULL
        ORDER BY year DESC
    """
    async with connect() as db:
        db.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        rows = await (await db.execute(sql)).fetchall()
    return [r["year"] for r in rows if r["year"]]
