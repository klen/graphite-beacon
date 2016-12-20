from __future__ import division

import re

NUMBER_RE = re.compile(r'(?P<value>\-?\d*\.?\d*)(?P<unit>\w+)')

# Time units
MILLISECOND = 'millisecond'
SECOND = 'second'
MINUTE = 'minute'
HOUR = 'hour'
DAY = 'day'
WEEK = 'week'
MONTH = 'month'
YEAR = 'year'


class TimeUnit(object):
    """A duration of time with a unit granularity."""

    UNIT_ALISES = {
        MILLISECOND: ['ms'],
        SECOND: ['s'],
        MINUTE: ['m'],
        HOUR: ['h'],
        DAY: ['d'],
        WEEK: ['w'],
        MONTH: ['M'],
        YEAR: ['y'],
    }
    UNIT_ALIASES_REVERSE = {a: unit for unit, aliases in UNIT_ALISES.items()
                            for a in aliases}

    UNITS_IN_SECONDS = {
        MILLISECOND: 0.001,
        SECOND: 1,
        MINUTE: 60,
        HOUR: 3600,
        DAY: 86400,
        WEEK: 604800,
        MONTH: 2592000,
        YEAR: 31536000,
    }
    UNITS_IN_MILLISECONDS = {k: v * 1000 for k, v in UNITS_IN_SECONDS.items()}

    UNITS_TO_GRAPHITE = {
        SECOND: 's',
        MINUTE: 'min',
        HOUR: 'h',
        DAY: 'd',
        WEEK: 'w',
        MONTH: 'mon',
        YEAR: 'y',
    }

    def __init__(self, value, unit):
        try:
            self.value = float(value)
        except ValueError:
            raise ValueError("Time unit values must be floats: {}".format(value))
        self.unit = self._normalize_unit(unit)

        if self.value < 0:
            raise ValueError("Negative time units are not supported: {}".format(value))
        if not self.unit:
            raise ValueError("Unable to parse time unit: {}{}".format(value, unit))

    def display_value(self):
        return int(self.value) if self.value.is_integer() else self.value

    @classmethod
    def from_interval(cls, interval):
        match = None
        try:
            match = NUMBER_RE.search(interval)
        except TypeError:
            pass
        if not match:
            raise ValueError("Unable to parse interval: {}".format(interval))
        return cls(match.group('value'), match.group('unit'))

    def __repr__(self):
        return '{}{}'.format(self.display_value(), self.unit)

    def as_tuple(self):
        return (self.value, self.unit)

    def __add__(self, other):
        if not isinstance(other, TimeUnit):
            raise ValueError("Cannot add object that is not a TimeUnit")
        result_ms = self.convert_to(MILLISECOND) + other.convert_to(MILLISECOND)
        return TimeUnit(self.convert(result_ms, MILLISECOND, self.unit), self.unit)

    def __sub__(self, other):
        if not isinstance(other, TimeUnit):
            raise ValueError("Cannot subtract object that is not a TimeUnit")
        result_ms = self.convert_to(MILLISECOND) - other.convert_to(MILLISECOND)
        return TimeUnit(self.convert(result_ms, MILLISECOND, self.unit), self.unit)

    @classmethod
    def _normalize_value_ms(cls, value):
        """Normalize a value in ms to the largest unit possible without decimal places.

        Note that this ignores fractions of a second and always returns a value _at least_
        in seconds.

        :return: the normalized value and unit name
        :rtype: Tuple[Union[int, float], str]
        """
        value = round(value / 1000) * 1000  # Ignore fractions of second

        sorted_units = sorted(cls.UNITS_IN_MILLISECONDS.items(),
                              key=lambda x: x[1], reverse=True)
        for unit, unit_in_ms in sorted_units:
            unit_value = value / unit_in_ms
            if unit_value.is_integer():
                return int(unit_value), unit
        return value, MILLISECOND  # Should never get here

    @classmethod
    def _normalize_unit(cls, unit):
        """Resolve a unit to its real name if it's an alias.

        :param unit str: the unit to normalize
        :return: the normalized unit, or None one isn't found
        :rtype: Union[None, str]
        """
        if unit in cls.UNITS_IN_SECONDS:
            return unit
        return cls.UNIT_ALIASES_REVERSE.get(unit, None)

    def as_graphite(self):
        # Graphite does not support decimal numbers, so normalize to an integer
        value, unit = self._normalize_value_ms(self.convert_to(MILLISECOND))

        # Edge case where the value fits into every unit, so just use the original
        # unless it is MILLISECOND
        if value == 0:
            unit = SECOND if self.unit == MILLISECOND else self.unit

        assert unit in self.UNITS_TO_GRAPHITE
        return '{}{}'.format(int(value), self.UNITS_TO_GRAPHITE[unit])

    def convert_to(self, unit):
        return TimeUnit.convert(self.value, self.unit, unit)

    @classmethod
    def convert(cls, value, from_unit, to_unit):
        """Convert a value from one time unit to another.

        :return: the numeric value converted to the desired unit
        :rtype: float
        """
        value_ms = value * cls.UNITS_IN_MILLISECONDS[from_unit]
        return value_ms / cls.UNITS_IN_MILLISECONDS[to_unit]
