class GraphiteRecord(object):

    def __init__(self, metric_string):
        meta, data = metric_string.split('|')
        self.target, start_time, end_time, step = meta.rsplit(',', 3)
        self.start_time = int(start_time)
        self.end_time = int(end_time)
        self.step = int(step)
        self.values = list(self._values(data.rsplit(',')))
        if len(self.values) == 0:
            raise ValueError('No data')

    @staticmethod
    def _values(values):
        for value in values:
            try:
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
