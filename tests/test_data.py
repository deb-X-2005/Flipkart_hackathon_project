import pandas as pd

from src.data.preprocess import clean, featurize


def test_clean_normalizes_column_names():
    df = pd.DataFrame({"Event Type": ["Planned"], "Latitude": ["12.97"]})
    out = clean(df)
    assert "event_type" in out.columns and "latitude" in out.columns
    assert out["event_type"].iloc[0] == "planned"


def test_clean_coerces_numeric():
    df = pd.DataFrame({"latitude": ["12.97", "bad"], "longitude": ["77.59", None]})
    out = clean(df)
    assert pd.isna(out["latitude"].iloc[1])
    assert out["latitude"].iloc[0] == 12.97


def test_featurize_derives_hour_dow_duration():
    df = pd.DataFrame({
        "start_datetime": pd.to_datetime(["2024-03-15 10:30:00", "2024-03-16 22:00:00"]),
        "end_datetime":   pd.to_datetime(["2024-03-15 11:00:00", "2024-03-16 22:30:00"]),
    })
    out = featurize(df)
    assert list(out["hour"]) == [10, 22]
    assert out["duration_min"].iloc[0] == 30.0
    assert set(out["dow"].tolist()) <= set(range(7))
    assert "is_weekend" in out.columns


def test_cache_get_put(isolated_cache):
    isolated_cache.put("k1", {"x": 1, "list": [1, 2, 3]}, ttl_seconds=60)
    assert isolated_cache.get("k1") == {"x": 1, "list": [1, 2, 3]}


def test_cache_expiry(isolated_cache):
    isolated_cache.put("k1", "value", ttl_seconds=-1)
    assert isolated_cache.get("k1") is None


def test_cache_purge_expired(isolated_cache):
    isolated_cache.put("expired", 1, ttl_seconds=-1)
    isolated_cache.put("fresh", 2, ttl_seconds=60)
    n = isolated_cache.purge_expired()
    assert n >= 1
    assert isolated_cache.get("fresh") == 2
