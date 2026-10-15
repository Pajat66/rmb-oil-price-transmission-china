"""Canonical inputs for the historical S3 lag audit; runtime interface untested."""
from phase15_common import REV,load_canonical
def load_long_sample():return load_canonical('long')
def load_short_sample():return load_canonical('short')
