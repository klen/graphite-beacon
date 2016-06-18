class GraphiteRecord(object):

    def __init__(self, metric_string, default_nan_value=None, ignore_nan=False):
        meta, data = metric_string.split('|')
        self.target, start_time, end_time, step = meta.rsplit(',', 3)
        self.start_time = int(start_time)
        self.end_time = int(end_time)
        self.step = int(step)
        self.default_nan_value = default_nan_value
        self.ignore_nan = ignore_nan
        self.values = list(self._values(data.rsplit(',')))
        if len(self.values) == 0:
            self.empty = True
        else:
            self.empty = False

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

    @property
    def median(self):
        return self.percentile(50)

    def percentile(self, rank):
        if rank == 100:
            return self.last_value()
        values = sorted(self.values)
        k = len(values) * rank / 100.0
        floor_k = int(k)
        return (floor_k + 1 - k) * values[floor_k] + (k - floor_k) * values[floor_k + 1]
