import pytest

from graphite_beacon.graphite import GraphiteRecord

from ..util import build_graphite_response


build_record = lambda data: GraphiteRecord(build_graphite_response(data=data))


class TestGraphiteRecord(object):
    def test_invalid_record(self):
        with pytest.raises(ValueError):
            GraphiteRecord('not,legit,data')

    def test_invalid_record_long(self):
        with pytest.raises(ValueError) as e:
            GraphiteRecord('<http>' + ('<tag>' * 50))
        assert '<http>' in str(e.value)
        assert str(e.value).endswith('..')

    def test_record(self):
        assert build_record([1, 2, 3]).values == [1.0, 2.0, 3.0]

    def test_average(self):
        assert build_record([1]).average == 1.0
        assert build_record([1, 2, 3]).average == 2.0
        assert build_record([5, 5, 5, 10]).average == 6.25
        assert build_record([1.5, 2.5, 3.5]).average == 2.5

    def test_last_value(self):
        assert build_record([1]).last_value == 1.0
        assert build_record([1, 2, 3]).last_value == 3.0

    def test_sum(self):
        assert build_record([1]).sum == 1.0
        assert build_record([1.5, 2.5, 3]).sum == 7.0

    def test_minimum(self):
        assert build_record([1]).minimum == 1.0
        assert build_record([9.0, 2.3, 4]).minimum == 2.3

    def test_maximum(self):
        assert build_record([1]).maximum == 1.0
        assert build_record([9.0, 2.3, 4]).maximum == 9.0
