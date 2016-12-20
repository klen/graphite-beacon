class GraphiteRecord(object):

    def __init__(self, metric_string, default_nan_value=None, ignore_nan=False):
        try:
            meta, data = metric_string.split('|')
        except ValueError:
            peek = ((metric_string[:40] + '..')
                    if len(metric_string) > 40 else metric_string)
            raise ValueError("Unable to parse graphite record: {}".format(peek))

        self.target, start_time, end_time, step = meta.rsplit(',', 3)
        self.start_time = int(start_time)
        self.end_time = int(end_time)
        self.step = int(step)
        self.default_nan_value = default_nan_value
        self.ignore_nan = ignore_nan
        self.values = list(self._values(data.rsplit(',')))
        self.empty = len(self.values) == 0

    def _values(self, values):
        for value in values:
            try:
                if self.ignore_nan and float(value) == self.default_nan_value:
                    continue
                yield float(value)
            except ValueError:
                continue

    @property
    def average(self):
        return self.sum / len(self.values)

    @property
    def last_value(self):
        return self.values[-1]

    @property
    def sum(self):
        return sum(self.values)

    @property
    def minimum(self):
        return min(self.values)

    @property
    def maximum(self):
        return max(self.values)
