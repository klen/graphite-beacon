import random

from graphite_beacon._compat import StringIO


def build_graphite_response(target_name='*', start_timestamp=1480000000,
                            end_timestamp=1480000050, series_step=60,
                            data=None):
    """Build a graphite response.

    Format: <target name>,<start timestamp>,<end timestamp>,<series step>|[data]*

    :param target_name str: the target query being fulfilled
    :param start_timestamp int: unix timestamp for query start
    :param end_timestamp int: unix timestamp for query end
    :param series_step int: the length of time between each step
    :param data list: query results
    :rtype: StringIO
    """
    data = data or []
    return StringIO(
        "{},{},{},{}|{}".format(target_name, start_timestamp, end_timestamp,
                                series_step, ','.join(str(d) for d in data))
    )
