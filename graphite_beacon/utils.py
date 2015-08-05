from re import compile as re
import operator as op

from funcparserlib.lexer import make_tokenizer, Token
from funcparserlib.parser import (some, a, maybe, finished, skip, many)


NUMBER_RE = re('(\d*\.?\d*)')
CONVERT = {
    "bytes": (
        ("TB", 1099511627776), ("GB", 1073741824.0), ("MB", 1048576.0), ("KB", 1024.0),
    ),
    "bits": (
        ("Tb", 1099511627776), ("Gb", 1073741824.0), ("Mb", 1048576.0), ("Kb", 1024.0),
    ),
    "bps": (
        ("Gbps", 1000000000.0), ("Mbps", 1000000.0), ("Kbps", 1000.0),
    ),
    "short": (
        ("Tri", 1000000000000.0), ("Bil", 1000000000.0), ("Mil", 1000000.0), ("K",   1000.0),
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
CONVERT_HASH = dict((name, value) for _types in CONVERT.values() for (name, value) in _types)
CONVERT['ms'] = list((n, v * 1000) for n, v in CONVERT['s'])
CONVERT_HASH['%'] = 1
TIME_UNIT_SIZE = dict(CONVERT['ms'])
TIME_UNIT_SYN = {"microsecond": "ms", "second": "s", "minute": "m", "hour": "h", "day": "d",
                 "week": "w", "month": "M", "year": "y"}
TIME_UNIT_SYN2 = dict([(v, n) for (n, v) in TIME_UNIT_SYN.items()])
IDENTITY = lambda x: x


HISTORICAL = 'historical'
COMPARATORS = {'>': op.gt, '>=': op.ge, '<': op.lt, '<=': op.le, '==': op.eq, '!=': op.ne}
OPERATORS = {'*': op.mul, '/': op.truediv, '+': op.add, '-': op.sub}
LOGICAL_OPERATORS = {'AND': op.and_, 'OR': op.or_}

RULE_TOKENIZER = make_tokenizer(
    [
        (u'Level', (r'(critical|warning|normal)',)),
        (u'Historical', (HISTORICAL,)),
        (u'Comparator', (r'({0})'.format('|'.join(sorted(COMPARATORS.keys(), reverse=True))),)),
        (u'LogicalOperator', (r'({0})'.format('|'.join(LOGICAL_OPERATORS.keys())),)),
        (u'Sep', (r':',)),
        (u'Operator', (r'(?:\*|\+|-|\/)',)),
        (u'Number', (r'(\d+\.?\d*)',)),
        (u'Unit', (r'({0})'.format('|'.join(sorted(CONVERT_HASH.keys(), reverse=True))),)),
        (u'Space', (r'\s+',))
    ]
)


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


def convert_from_format(num, unit=None):
    if not unit:
        return float(num)
    return float(num) * CONVERT_HASH.get(unit, 1)


def parse_interval(interval):
    """ Convert 1.2day to 103680000.0 (ms)"""
    _, num, unit = NUMBER_RE.split(str(interval))
    num = float(num)
    return num * TIME_UNIT_SIZE.get(unit, TIME_UNIT_SIZE[TIME_UNIT_SYN.get(unit, 's')])


def interval_to_graphite(interval):
    _, num, unit = NUMBER_RE.split(interval)
    unit = TIME_UNIT_SYN2.get(unit, unit) or 'second'
    return num + unit


def _tokenize_rule(_str):
    return [x for x in RULE_TOKENIZER(_str) if x.type not in ['Space']]


def _parse_rule(seq):
    tokval = lambda x: x.value
    toktype = lambda t: some(lambda x: x.type == t) >> tokval
    sep = lambda s: a(Token(u'Sep', s)) >> tokval
    s_sep = lambda s: skip(sep(s))

    level = toktype(u'Level')
    comparator = toktype(u'Comparator') >> COMPARATORS.get
    number = toktype(u'Number') >> float
    historical = toktype(u'Historical')
    unit = toktype(u'Unit')
    operator = toktype(u'Operator')
    logical_operator = toktype(u'LogicalOperator') >> LOGICAL_OPERATORS.get

    exp = comparator + ((number + maybe(unit)) | historical) + maybe(operator + number)
    rule = (
        level + s_sep(':') + exp + many(logical_operator + exp)
    )

    overall = rule + skip(finished)
    return overall.parse(seq)


def _parse_expr(expr):
    cond, value, mod = expr

    if value != HISTORICAL:
        value = convert_from_format(*value)

    if mod:
        _op, num = mod
        mod = lambda x: OPERATORS[_op](x, num)

    return {'op': cond, 'value': value, 'mod': mod or IDENTITY}


def parse_rule(rule):
    tokens = _tokenize_rule(rule)
    level, initial_expr, exprs = _parse_rule(tokens)

    result = {'level': level, 'raw': rule, 'exprs': [_parse_expr(initial_expr)]}

    for logical_operator, expr in exprs:
        result['exprs'].extend([logical_operator, _parse_expr(expr)])

    return result
