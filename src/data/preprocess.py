"""Clean + feature-engineer event data."""
import pandas as pd


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for col in ("start_datetime", "end_datetime"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ("latitude", "longitude", "endlatitude", "endlongitude"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ("event_type", "event_cause"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().str.lower()
    return df


def featurize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "start_datetime" in df.columns:
        s = df["start_datetime"]
        df["dow"] = s.dt.dayofweek
        df["hour"] = s.dt.hour
        df["month"] = s.dt.month
        df["is_weekend"] = df["dow"].isin([5, 6]).astype("Int64")
        # Reporting-time bias: EDA showed events spike 04-08 and 19-23, near-zero 09-17.
        # That's a logging artifact (overnight truck breakdowns reported on shift change,
        # etc.), not actual incident timing. Flag it so downstream models can either
        # exclude or down-weight the bias hours.
        df["is_reporting_window"] = (
            df["hour"].between(4, 8) | df["hour"].between(19, 23)
        ).astype("Int64")
    if {"start_datetime", "end_datetime"}.issubset(df.columns):
        df["duration_min"] = (
            (df["end_datetime"] - df["start_datetime"]).dt.total_seconds() / 60
        )
    return df
