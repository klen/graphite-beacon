import subprocess

from . import AbstractHandler, LOGGER


class CliHandler(AbstractHandler):

    name = 'cli'

    # Default options
    defaults = {
        'command': None,
        'alerts_whitelist': [],
    }

    def init_handler(self):
        self.commandTemplate = self.options.get('command')
        self.whitelist = self.options.get('alerts_whitelist')
        assert self.commandTemplate, 'Command line command is not defined.'

    def _substituteVariables(self, command, level, name, value, target=None, **kwargs):
        '''
        Substitute variables in command fragments by values e.g. ${level} => 'warning'
        '''
        substitutes = {
            '${level}': str(level),
            '${target}': str(target),
            '${name}': '"' + str(name) + '"',
            '${value}': str(value),
            '${limit_value}': str(kwargs.get('rule', {}).get('value', '')),
        }

        result = command
        for pattern, value in substitutes.items():
            result = result.replace(pattern, value)

        return result

    def notify(self, level, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        def getAlertName(*args):
            name = str(args[0])
            # remove time characteristics e.g. (1minute)
            return name.rsplit(' ', 1)[0].strip()

        # Run only for whitelisted names if specified
        if not self.whitelist or getAlertName(*args) in self.whitelist:
            command = self._substituteVariables(self.commandTemplate, level, *args, **kwargs)
            subprocess.Popen(
                command,
                shell=True,
                stdin=None,
                stdout=None,
                stderr=None,
                close_fds=True)
