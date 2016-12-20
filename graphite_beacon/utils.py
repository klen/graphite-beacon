import operator as op
from re import compile as re

from funcparserlib.lexer import Token, make_tokenizer
from funcparserlib.parser import a, finished, many, maybe, skip, some

# NOTE: the unit conversions below should be considered deprecated and migrated
# over to `unit.py` instead.

NUMBER_RE = re(r'(\d*\.?\d*)')
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
        ("Tri", 1000000000000.0), ("Bil", 1000000000.0), ("Mil", 1000000.0), ("K", 1000.0),
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

IDENTITY = lambda x: x

HISTORICAL = 'historical'
COMPARATORS = {'>': op.gt, '>=': op.ge, '<': op.lt, '<=': op.le, '==': op.eq, '!=': op.ne}
OPERATORS = {'*': op.mul, '/': op.truediv, '+': op.add, '-': op.sub}
LOGICAL_OPERATORS = {'AND': op.and_, 'OR': op.or_}

RULE_TOKENIZER = make_tokenizer(
    [
        (u'Level', (r'(critical|warning|normal)',)),
        (u'Historical', (HISTORICAL,)),
        (u'Comparator', (r'({})'.format('|'.join(sorted(COMPARATORS.keys(), reverse=True))),)),
        (u'LogicalOperator', (r'({})'.format('|'.join(LOGICAL_OPERATORS.keys())),)),
        (u'Sep', (r':',)),
        (u'Operator', (r'(?:\*|\+|-|\/)',)),
        (u'Number', (r'(\d+\.?\d*)',)),
        (u'Unit', (r'({})'.format('|'.join(sorted(CONVERT_HASH.keys(), reverse=True))),)),
        (u'Space', (r'\s+',))
    ]
)


def convert_to_format(value, frmt=None):
    value = float(value)
    units = CONVERT.get(frmt, [])
    for name, size in units:
        if size < value:
            break
    else:
        return value

    value /= size  # pylint: disable=undefined-loop-variable
    value = ("%.1f" % value).rstrip('0').rstrip('.')
    return "{}{}".format(value, name)  # pylint: disable=undefined-loop-variable


def convert_from_format(num, unit=None):
    if not unit:
        return float(num)
    return float(num) * CONVERT_HASH.get(unit, 1)


def _tokenize_rule(_str):
    return [x for x in RULE_TOKENIZER(_str) if x.type not in ['Space']]


def _parse_rule(seq):
    tokval = lambda x: x.value
    toktype = lambda t: some(lambda x: x.type == t) >> tokval  # pylint: disable=undefined-variable
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
