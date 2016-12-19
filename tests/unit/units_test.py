import pytest

from graphite_beacon.units import (
    DAY,
    HOUR,
    MILLISECOND,
    MINUTE,
    MONTH,
    SECOND,
    TimeUnit,
    YEAR,
)

class TestTimeUnit(object):
    def test_from_interval(self):
        assert TimeUnit.from_interval('2second').as_tuple() == (2, SECOND)
        assert TimeUnit.from_interval('2.5second').as_tuple() == (2.5, SECOND)

    def test_from_interval_invalid(self):
        inputs = [None, '', 'minute1', '-1minute', '2meter']
        for i in inputs:
            with pytest.raises(ValueError):
                TimeUnit.from_interval(i)

    def test_convert(self):
        assert TimeUnit.convert(10, SECOND, MILLISECOND) == 10000
        assert TimeUnit.convert(1, MILLISECOND, SECOND) == 0.001
        assert TimeUnit.convert(10, MINUTE, SECOND) == 600
        assert TimeUnit.convert(1.2, DAY, MILLISECOND) == 103680000

    def test_str(self):
        assert str(TimeUnit(0, MILLISECOND)) == "0millisecond"
        assert str(TimeUnit(10, SECOND)) == "10second"
        assert str(TimeUnit(2, YEAR)) == "2year"

    def test_arithmetic(self):
        assert (TimeUnit(10, SECOND) - TimeUnit(5, SECOND)).as_tuple() == (5, SECOND)
        assert (TimeUnit(10, SECOND) + TimeUnit(5, SECOND)).as_tuple() == (15, SECOND)

        assert (TimeUnit(50, SECOND) + TimeUnit(70, SECOND)).as_tuple() == (120, SECOND)
        assert (TimeUnit(50, SECOND) + TimeUnit(71, SECOND)).as_tuple() == (121, SECOND)

        assert (TimeUnit(0, SECOND) + TimeUnit(0, SECOND)).as_tuple() == (0, SECOND)
        assert (TimeUnit(0, MILLISECOND) + TimeUnit(0, MILLISECOND)).as_tuple() == (0, MILLISECOND)
        assert (TimeUnit(0, SECOND) + TimeUnit(0, YEAR)).as_tuple() == (0, SECOND)

        assert (TimeUnit(0, SECOND) - TimeUnit(0, SECOND)).as_tuple() == (0, SECOND)
        assert (TimeUnit(0, MILLISECOND) - TimeUnit(0, MILLISECOND)).as_tuple() == (0, MILLISECOND)
        assert (TimeUnit(0, SECOND) - TimeUnit(0, YEAR)).as_tuple() == (0, SECOND)

    def test_arithmetic_decimal(self):
        assert (TimeUnit(1.5, SECOND) + TimeUnit(1, SECOND)).as_tuple() == (2.5, SECOND)

    def test_as_graphite(self):
        assert TimeUnit(10, MINUTE).as_graphite() == '10min'
        assert TimeUnit(875, SECOND).as_graphite() == '875s'
        assert TimeUnit(2, HOUR).as_graphite() == '2h'
        assert TimeUnit(1, MONTH).as_graphite() == '1mon'

    def test_as_graphite_decimal(self):
        assert TimeUnit(1.5, MONTH).as_graphite() == '45d'
        assert TimeUnit(5.1, DAY).as_graphite() == '7344min'
        assert TimeUnit(1.5, YEAR).as_graphite() == '13140h'
        assert TimeUnit(1, MILLISECOND).as_graphite() == '0s'
        assert TimeUnit(501, MILLISECOND).as_graphite() == '1s'
