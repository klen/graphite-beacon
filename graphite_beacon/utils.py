from re import compile as re


CONVERT = {
    "bytes": (
        ("GB", 1000000000.0),
        ("MB", 1000000.0),
        ("KB", 1000.0),
    ),
    "short": (
        ("Tri", 1000000000000.0),
        ("Bil", 1000000000.0),
        ("Mil", 1000000.0),
        ("K",   1000.0),
    ),
    "s": (
        ("y", 31536000.0),
        ("M", 2592000.0),
        ("w", 604800.0),
        ("d", 86400.0),
        ("h", 3600.0),
        ("m", 60.0),
        ("s", 1.0),
        ("ms", 0.001),
    ),
    "percent": (
        ("%", 1),
        ("%", .01),
    )
}
CONVERT['ms'] = list((n, v * 1000) for n, v in CONVERT['s'])
TIME_RE = re('(\d+)')
TIME_UNIT_SIZE = {
    "second": 1000,
    "minute": 60 * 1000,
    "hour": 60 * 60 * 1000,
    "day": 24 * 60 * 60 * 1000,
    "month": 30 * 24 * 60 * 60 * 1000,
    "year": 365.2425 * 24 * 60 * 60 * 1000
}


def convert(value, frmt):
    units = CONVERT.get(frmt, [])
    for name, size in units:
        if size < value:
            break
    else:
        return value

    if size != 1:
        value /= size
        value = ("%.1f" % value).rstrip('0').rstrip('.')
    return "%s%s" % (value, name)


def parse_interval(interval):
    _, count, unit = TIME_RE.split(interval)
    return int(count) * TIME_UNIT_SIZE.get(unit, 1000)
