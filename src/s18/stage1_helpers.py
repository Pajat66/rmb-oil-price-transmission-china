"""Original S18 calendar/hash numerical helpers; no estimation entry point."""
import numpy as np
import pandas as pd
import hashlib

def calendar(frame):
    dates = pd.to_datetime(frame["month"], errors="raise")
    periods = pd.PeriodIndex(dates, freq="M")
    assert not periods.has_duplicates and not dates.isna().any()
    assert np.all(dates.dt.day == 1), "Source dates must be real month starts"
    assert periods.equals(pd.period_range(periods.min(), periods.max(), freq="M"))
    return periods


def lookup(frame, variable, offset):
    ix = pd.PeriodIndex(frame.month, freq="M")
    values = pd.Series(frame[variable].to_numpy(float), index=ix)
    return values.reindex(ix + offset).to_numpy(float)


def month_hash(months):
    return hashlib.sha256("|".join(months).encode("utf-8")).hexdigest()


def array_hash(a):
    v = np.ascontiguousarray(a, dtype="<f8")
    h = hashlib.sha256()
    h.update(str(v.shape).encode("ascii"))
    h.update(v.tobytes())
    return h.hexdigest()

