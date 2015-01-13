import subprocess

from . import AbstractHandler, LOGGER


class CliHandler(AbstractHandler):

    name = 'cli'

    # Default options
    defaults = {
        'command': None,
    }


    def init_handler(self):
        self.command = self.options.get('command')
        assert self.command, 'Command line command is not defined.'


    def _substituteVariables(self, fragments, level, *args):
        '''
        Substitute variables in command fragments by values e.g. ${level} => 'warning'
        '''
        name, value = args

        substitutes = {
            '${level}': str(level),
            '${name}': '"' + str(name) + '"',
            '${value}': str(value),
        }

        for i, fragment in enumerate(fragments):
            for pattern, value in substitutes.items():
                if pattern in fragment:
                    fragments[i] = fragment.replace(pattern, value)

        return fragments


    def notify(self, level, *args, **kwargs):
        LOGGER.debug("Handler (%s) %s", self.name, level)

        fragments = self._substituteVariables(self.command.split(' '), level, *args)
        returncode = subprocess.call(fragments)

        if returncode:
            LOGGER.error('CLI Command call returned non-zero code = %s. Command = %s', returncode, ' '.join(fragments))

