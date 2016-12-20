import subprocess

from graphite_beacon.handlers import LOGGER, AbstractHandler


class CliHandler(AbstractHandler):

    name = 'cli'

    # Default options
    defaults = {
        'command': None,
        'alerts_whitelist': [],
    }

    def init_handler(self):
        self.command_template = self.options.get('command')
        self.whitelist = self.options.get('alerts_whitelist')
        assert self.command_template, 'Command line command is not defined.'

    def notify(self, level, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        def get_alert_name(*args):
            name = str(args[0])
            # remove time characteristics e.g. (1minute)
            return name.rsplit(' ', 1)[0].strip()

        # Run only for whitelisted names if specified
        if not self.whitelist or get_alert_name(*args) in self.whitelist:
            command = substitute_variables(self.command_template, level, *args, **kwargs)
            subprocess.Popen(
                command,
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True)


def substitute_variables(command, level, name, value, target=None, **kwargs):
    """Substitute variables in command fragments by values e.g. ${level} => 'warning'."""
    rule = kwargs.get('rule', {})
    rule_value = rule.get('value', '') if rule else ''
    substitutes = {
        '${level}': str(level),
        '${target}': str(target),
        '${name}': '"' + str(name) + '"',
        '${value}': str(value),
        '${limit_value}': str(rule_value),
    }

    result = command
    for pattern, value in substitutes.items():
        result = result.replace(pattern, value)

    return result
