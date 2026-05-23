from fastapi import HTTPException

from .cache import cache
from .database import BOOKING_TABLE, assert_known_column, fetch_all_dicts, fetch_one_dict, table_columns, table_exists

# determines which table in the noshow.db that gets queried
SCORED_BOOKING_TABLE = "booking_ml_scores"

SEGMENT_DIMENSIONS = [
    "branch",
    "platform",
    "country",
    "room",
    "customer_status",
    "booking_month",
    "arrival_month",
    "price_band",
]
MONTH_COLUMNS = {"booking_month", "arrival_month", "checkout_month"}

ML_SCORE_COLUMNS = [
    "ml_risk_logistic_regression",
    "ml_risk_decision_tree",
    "ml_risk_random_forest",
    "ml_risk_extra_trees",
    "ml_risk_gradient_boosting",
]
PRICE_NUMERIC_SQL = (
    "CAST(REPLACE(REPLACE(REPLACE(REPLACE(CAST(price AS TEXT), 'SGD$', ''), '$', ''), ',', ''), ' ', '') AS REAL)"
)


def active_analytics_table() -> str:
    return SCORED_BOOKING_TABLE if table_exists(SCORED_BOOKING_TABLE) else BOOKING_TABLE


def normalize_month(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"", "nan", "none", "null"}:
        return None
    return text[:1].upper() + text[1:]


def normalized_dimension_expr(dimension: str) -> str:
    if dimension == "customer_status":
        return (
            "CASE "
            "WHEN first_time_flag = 1 THEN 'First-time' "
            "WHEN first_time_flag = 0 THEN 'Returning' "
            "ELSE 'Missing' END"
        )
    if dimension not in MONTH_COLUMNS:
        return f"COALESCE(CAST({dimension} AS TEXT), 'Missing')"
    cleaned = f"LOWER(TRIM(CAST({dimension} AS TEXT)))"
    return (
        f"CASE WHEN {dimension} IS NULL OR {cleaned} IN ('', 'nan', 'none', 'null') "
        f"THEN 'Missing' "
        f"ELSE UPPER(SUBSTR({cleaned}, 1, 1)) || SUBSTR({cleaned}, 2) END"
    )


def available_dimensions() -> list[str]:
    columns = set(table_columns(active_analytics_table()))
    dimensions = []
    for column in SEGMENT_DIMENSIONS:
        if column == "customer_status":
            if "first_time_flag" in columns:
                dimensions.append(column)
        elif column in columns:
            dimensions.append(column)
    return dimensions


def summary_metrics() -> dict:
    table_name = active_analytics_table()
    cache_key = f"summary:{table_name}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    columns = set(table_columns(table_name))
    price_expr = f"COALESCE(SUM(CASE WHEN no_show = 1 THEN {PRICE_NUMERIC_SQL} ELSE 0 END), 0)" if "price" in columns else "NULL"
    avg_price_expr = f"AVG({PRICE_NUMERIC_SQL})" if "price" in columns else "NULL"
    row = fetch_one_dict(
        f"""
        SELECT
            COUNT(*) AS total_bookings,
            AVG(no_show) AS no_show_rate,
            SUM(no_show) AS no_shows,
            {avg_price_expr} AS avg_price,
            {price_expr} AS observed_revenue_at_risk
        FROM {table_name}
        """
    )
    row["available_dimensions"] = available_dimensions()
    return cache.set(cache_key, row)


def segment_summary(dimension: str, min_bookings: int = 20, limit: int = 20) -> list[dict]:
    try:
        table_name = active_analytics_table()
        if dimension != "customer_status":
            dimension = assert_known_column(dimension, table_name)
        elif "first_time_flag" not in table_columns(table_name):
            raise ValueError("Unknown column: customer_status")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    cache_key = f"segment:{table_name}:{dimension}:{min_bookings}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    columns = set(table_columns(table_name))
    segment_expr = normalized_dimension_expr(dimension)
    price_cols = f"AVG({PRICE_NUMERIC_SQL}) AS avg_price, COALESCE(SUM(CASE WHEN no_show = 1 THEN {PRICE_NUMERIC_SQL} ELSE 0 END), 0) AS observed_revenue_at_risk"
    if "price" not in columns:
        price_cols = "NULL AS avg_price, NULL AS observed_revenue_at_risk"

    rows = fetch_all_dicts(
        f"""
        SELECT
            {segment_expr} AS segment,
            COUNT(*) AS bookings,
            SUM(no_show) AS no_shows,
            AVG(no_show) AS no_show_rate,
            {price_cols}
        FROM {table_name}
        GROUP BY {segment_expr}
        HAVING COUNT(*) >= :min_bookings
        ORDER BY no_show_rate DESC, bookings DESC
        LIMIT :limit
        """,
        {"min_bookings": min_bookings, "limit": limit},
    )
    return cache.set(cache_key, rows)


def high_risk_bookings(limit: int = 50, risk_band: str | None = None) -> list[dict]:
    if not table_exists(SCORED_BOOKING_TABLE):
        raise HTTPException(
            status_code=409,
            detail="ML score table 'booking_ml_scores' not found. Rerun the notebook ML scoring cell first.",
        )

    normalized_band = risk_band.title() if risk_band else None
    if normalized_band == "All":
        normalized_band = None
    if normalized_band and normalized_band not in {"High", "Medium", "Low"}:
        raise HTTPException(status_code=400, detail="risk_band must be High, Medium, Low, or All")

    cache_key = f"ml_risk_queue:{limit}:{normalized_band or 'all'}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    columns = table_columns(SCORED_BOOKING_TABLE)
    selected = [
        column
        for column in [
            "booking_id",
            "branch",
            "platform",
            "country",
            "room",
            "first_time_flag",
            "price",
            "price_numeric",
            "no_show",
            "risk_score",
            "predicted_no_show_probability",
            "risk_band",
            "expected_revenue_at_risk",
            *ML_SCORE_COLUMNS,
        ]
        if column in columns
    ]
    if "first_time_flag" in columns:
        selected.append(
            "CASE "
            "WHEN first_time_flag = 1 THEN 'First-time' "
            "WHEN first_time_flag = 0 THEN 'Returning' "
            "ELSE 'Missing' END AS customer_status"
        )
    where_clause = "WHERE risk_band = :risk_band" if normalized_band else ""
    params = {"risk_band": normalized_band} if normalized_band else {}
    rows = fetch_all_dicts(
        f"""
        SELECT {', '.join(selected)}
        FROM {SCORED_BOOKING_TABLE}
        {where_clause}
        ORDER BY expected_revenue_at_risk DESC, risk_score DESC
        LIMIT :limit
        """,
        {**params, "limit": limit},
    )
    return cache.set(cache_key, rows)


def predict(payload: dict) -> dict:
    if not table_exists(SCORED_BOOKING_TABLE):
        raise HTTPException(
            status_code=409,
            detail="ML score table 'booking_ml_scores' not found. Rerun the notebook ML scoring cell first.",
        )

    columns = set(table_columns(SCORED_BOOKING_TABLE))
    filters = []
    params = {}
    for column in ["branch", "platform", "country", "room"]:
        value = payload.get(column)
        if value is not None and column in columns:
            filters.append(f"LOWER(CAST({column} AS TEXT)) = LOWER(:{column})")
            params[column] = str(value)

    first_time_flag = payload.get("first_time_flag")
    customer_status = payload.get("customer_status")
    if first_time_flag is None and customer_status is not None:
        status_text = str(customer_status).strip().lower()
        if status_text in {"first-time", "first time", "first", "yes", "true", "1"}:
            first_time_flag = 1
        elif status_text in {"returning", "repeat", "no", "false", "0"}:
            first_time_flag = 0
    if first_time_flag is not None and "first_time_flag" in columns:
        filters.append("CAST(first_time_flag AS INTEGER) = :first_time_flag")
        params["first_time_flag"] = int(first_time_flag)

    if not filters:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one segment field: branch, platform, country, room, or first_time_flag.",
        )

    where_clause = " AND ".join(filters)
    price_value = payload.get("price")
    expected_revenue_expr = "AVG(expected_revenue_at_risk)"
    if price_value is not None:
        expected_revenue_expr = ":price * AVG(predicted_no_show_probability)"
        params["price"] = float(price_value)

    row = fetch_one_dict(
        f"""
        SELECT
            COUNT(*) AS matched_bookings,
            AVG(predicted_no_show_probability) AS predicted_no_show_probability,
            AVG(risk_score) AS risk_score,
            {expected_revenue_expr} AS expected_revenue_at_risk
        FROM {SCORED_BOOKING_TABLE}
        WHERE {where_clause}
        """,
        params,
    )
    if not row or not row.get("matched_bookings"):
        raise HTTPException(status_code=404, detail="No historical scored bookings match the supplied fields.")

    probability = row.get("predicted_no_show_probability") or 0
    if probability >= 0.40:
        risk_band = "High"
    elif probability >= 0.30:
        risk_band = "Medium"
    else:
        risk_band = "Low"

    return {
        "model_source": "booking_ml_scores_segment_average",
        "matched_bookings": int(row["matched_bookings"]),
        "predicted_no_show_probability": probability,
        "risk_score": row.get("risk_score") or probability,
        "risk_band": risk_band,
        "expected_revenue_at_risk": row.get("expected_revenue_at_risk") or 0,
        **{key: value for key, value in payload.items() if value is not None},
    }


def top_insights() -> list[dict]:
    insights = []
    summary = summary_metrics()
    insights.append(
        {
            "title": "Overall no-show exposure",
            "text": f"{summary['total_bookings']:,} bookings with a {summary['no_show_rate']:.1%} no-show rate and {summary.get('observed_revenue_at_risk') or 0:,.0f} observed revenue at risk.",
            "score": 1.0,
        }
    )
    for dimension in available_dimensions()[:6]:
        rows = segment_summary(dimension, min_bookings=50, limit=3)
        for row in rows:
            insights.append(
                {
                    "title": f"{dimension}: {row['segment']}",
                    "text": f"{row['segment']} has {row['bookings']:,} bookings, a {row['no_show_rate']:.1%} no-show rate, and {row.get('observed_revenue_at_risk') or 0:,.0f} observed revenue at risk.",
                    "score": row["no_show_rate"],
                }
            )
    return sorted(insights, key=lambda item: item["score"], reverse=True)


def average_probability(rows: list[dict]) -> float:
    values = [row["predicted_no_show_probability"] for row in rows if row.get("predicted_no_show_probability") is not None]
    return sum(values) / len(values) if values else 0.0
