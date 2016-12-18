import operator as op

import pytest

from funcparserlib.lexer import LexerError



from graphite_beacon.utils import (
    convert_to_format,
    convert_from_format,
    interval_to_graphite,
    parse_interval,
    parse_rule as parse_rule,
    IDENTITY
)


def test_convert():
    assert convert_to_format(789874) == 789874
    assert convert_from_format(789874)
    assert convert_to_format(45, 'percent') == "45%"
    assert convert_from_format('45', '%') == 45

    assert convert_to_format(789, 'bytes') == 789
    assert convert_to_format(456789, 'bytes') == '446.1KB'
    assert convert_from_format('456.8', 'KB') == 467763.2
    assert convert_to_format(45678912, 'bytes') == '43.6MB'
    assert convert_from_format('45.7', 'MB') == 47919923.2
    assert convert_to_format(4567891245, 'bytes') == '4.3GB'
    assert convert_from_format('4.6', 'GB') == 4939212390.4

    assert convert_from_format('456.8', 'Kb') == 467763.2
    assert convert_from_format('456.8', 'Kbps') == 456800

    assert convert_to_format(789, 'short') == 789
    assert convert_to_format(456789, 'short') == '456.8K'
    assert convert_from_format('456.8', 'K') == 456800
    assert convert_to_format(45678912, 'short') == '45.7Mil'
    assert convert_from_format('45.7', 'Mil') == 45700000
    assert convert_to_format(4567891245, 'short') == '4.6Bil'
    assert convert_from_format('4.6', 'Bil') == 4600000000

    assert convert_to_format(789, 's') == "13.2m"
    assert convert_from_format('13.2', 'm') == 792
    assert convert_to_format(789456, 's') == "1.3w"
    assert convert_from_format('1.3', 'w') == 786240
    assert convert_to_format(789456234, 's') == "25y"

    assert convert_to_format(79456234, 'ms') == "22.1h"
    assert convert_to_format(34, 'ms') == "34ms"


def test_parse_interval():
    assert parse_interval(10) == 10000.0
    assert parse_interval('10') == 10000.0
    assert parse_interval('15s') == 15000.0
    assert parse_interval('5minute') == 300000.0
    assert parse_interval('6m') == 360000.0
    assert parse_interval('1.2day') == 103680000.0
    assert parse_interval('4d') == 345600000.0
    assert parse_interval('5month') == 12960000000.0


def test_interval_to_graphite():
    assert interval_to_graphite('10m') == '10minute'
    assert interval_to_graphite('875') == '875second'
    assert interval_to_graphite('2hour') == '2hour'


def test_parse_rule():
    with pytest.raises(LexerError):
        assert parse_rule('invalid')

    assert parse_rule('normal: == 0') == {
        'level': 'normal', 'raw': 'normal: == 0',
        'exprs': [{'op': op.eq, 'value': 0, 'mod': IDENTITY}]}

    assert parse_rule('critical: < 30MB') == {
        'level': 'critical', 'raw': 'critical: < 30MB',
        'exprs': [{'op': op.lt, 'value': 31457280, 'mod': IDENTITY}]}

    assert parse_rule('warning: >= 30MB') == {
        'level': 'warning', 'raw': 'warning: >= 30MB',
        'exprs': [{'op': op.ge, 'value': 31457280, 'mod': IDENTITY}]}

    assert parse_rule('warning: >= historical') == {
        'level': 'warning', 'raw': 'warning: >= historical',
        'exprs': [{'op': op.ge, 'value': 'historical', 'mod': IDENTITY}]}

    assert parse_rule('warning: >= historical AND > 25') == {
        'level': 'warning', 'raw': 'warning: >= historical AND > 25',
        'exprs': [{'op': op.ge, 'value': 'historical', 'mod': IDENTITY},
                  op.and_,
                  {'op': op.gt, 'value': 25, 'mod': IDENTITY}]}

    rule = parse_rule('warning: >= historical * 1.2')
    assert rule['exprs'][0]['mod']
    assert rule['exprs'][0]['mod'](5) == 6
