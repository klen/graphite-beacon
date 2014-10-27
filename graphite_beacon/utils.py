from re import compile as re
import operator as op


NUMBER_RE = re('(\d*\.?\d*)')
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
    )
}
CONVERT_HASH = {name: value for _types in CONVERT.values() for (name, value) in _types}
CONVERT['ms'] = list((n, v * 1000) for n, v in CONVERT['s'])
CONVERT_HASH['%'] = 1
TIME_UNIT_SIZE = dict(CONVERT['ms'])
TIME_UNIT_SYN = {"microsecond": "ms", "second": "s", "minute": "m", "hour": "h", "day": "d",
                 "week": "w", "month": "M", "year": "y"}
TIME_UNIT_SYN2 = dict([(v, n) for (n, v) in TIME_UNIT_SYN.items()])


OPERATORS = {'>': op.gt, '>=': op.ge, '<': op.lt, '<=': op.le, '==': op.eq, '!=': op.ne}
RULE_RE = re(
    '(critical|warning|normal):\s+(%s)\s+(\d+\.?\d*(?:%s)?)' % (
        "|".join(OPERATORS.keys()),
        "|".join(sorted(CONVERT_HASH.keys(), reverse=True))
    ))


def convert_to_format(value, frmt=None):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return value

    units = CONVERT.get(frmt, [])
    for name, size in units:
        if size < value:
            break
    else:
        return value

    value /= size
    value = ("%.1f" % value).rstrip('0').rstrip('.')
    return "%s%s" % (value, name)


def convert_from_format(value):
    _, num, unit = NUMBER_RE.split(str(value))
    if not unit:
        return float(value)
    return float(num) * CONVERT_HASH.get(unit, 1)


def parse_interval(interval):
    _, num, unit = NUMBER_RE.split(interval)
    num = float(num)
    return num * TIME_UNIT_SIZE.get(unit, TIME_UNIT_SIZE[TIME_UNIT_SYN.get(unit, 's')])


def interval_to_graphite(interval):
    _, num, unit = NUMBER_RE.split(interval)
    unit = TIME_UNIT_SYN2.get(unit, unit) or 'second'
    return num + unit


def parse_rule(rule):
    match = RULE_RE.match(rule)
    if not match:
        raise ValueError('Invalid rule: %s' % rule)
    level, cond, value = match.groups()
    value = convert_from_format(value)
    if cond not in OPERATORS:
        raise ValueError('Invalid operator: %s for rule %s' % (cond, rule))
    op = OPERATORS.get(cond)
    return {'level': level, 'op': op, 'value': value}
