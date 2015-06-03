from librabbitmq import Connection

from . import AbstractHandler, LOGGER


class RabbitMQHandler(AbstractHandler):

    name = 'rabbitmq'

    # Default options
    defaults = {
        'user': 'guest',
        'password': 'guest',
        'host': 'localhost',
        'port': '5672',
        'virtualhost': '/',
        'exchange': None,
        'exchange_type': None,
        'queue': None
    }

    def init_handler(self):
        self.rmq_host = self.options.get('host')
        self.rmq_user = self.options.get('username')
        self.rmq_passwd = self.options.get('password')
        self.rmq_virtualhost = self.options.get('virtualhost')
        self.rmq_exchange = self.options.get('exchange')
        self.rmq_exchange_type = self.options.get('exchange_type')
        self.rmq_queue = self.options.get('queue')
        self.rmq_rkey = self.options.get('routing_key')

        conn = Connection(
            host=self.rmq_host,
            userid=self.rmq_user,
            password=self.rmq_passwd,
            virtualhost=self.rmq_virtualhost
        )
        self.channel = conn.channel()
        self.channel = exchange_declare(self.rmq_exchange, self.rmq_exchange)
        self.channel = queue_declare(self.rmq_queue)
        self.channel = queue_bind(self.rmq_queue, self.rmq_exchange, self.rmq_rkey)

    def notify(self, level, alert, value, target=None, ntype=None, rule=None):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        message = self.get_short(level, alert, value, target=target, ntype=ntype, rule=rule)
        data = {'alert': alert.name, 'desc': message, 'level': level}
        if target:
            data['target'] = target
        if rule:
            data['rule'] = rule['raw']
        data.update(self.params)
        self.channel.basic_publish(data, self.rmq_exchange, self.rmq_rkey)
