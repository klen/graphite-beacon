import json
from os.path import exists
import functools
from tornado import gen, httpclient

from graphite_beacon.handlers import AbstractHandler, LOGGER
from graphite_beacon.template import TEMPLATES

HELP_MESSAGE = """Telegram handler for graphite-beacon
usage: /command [parameters]
examples:
/activate my_token123
/deactivate my_token123
commands:
activate - activate bot and remember this chat (no need to activate every time)
deactivate - deactivate bot and forget this chat
help - see this message
every command must be preceded by slash symbol (/)
parameters:
bot_ident - mandatory for Telegram groups
parameters must be separated by whitespace
"""

BOT_COMMAND_ERRORS = {
    'wrong_ident': 'Could not parse command: wrong bot ident',
    'no_ident': 'Could not parse command: bot ident is missing',}

class TelegramHandler(AbstractHandler):

    name = 'telegram'

    # Default options
    defaults = {
        'token': None,
        'bot_ident': None,
        'chatfile': None
    }

    def init_handler(self):

        self.token = self.options.get('token')
        assert self.token, 'Telegram bot API token is not defined.'

        self.bot_ident = self.options.get('bot_ident')
        assert self.bot_ident, 'Telegram bot ident token is not defined.'

        file = self.options.get('chatfile')
        if not file:
            LOGGER.warning('chatfile not found in configs')
        elif not exists(file):
            LOGGER.error('chatfile specified in configs doesnt exist')
            file = None
        self.chatfile = file
        self.chats = get_chatlist(self.chatfile)

        self._client = httpclient.AsyncHTTPClient()
        self._url = 'https://api.telegram.org/bot%s/' % (self.token)
        self.getUpdates = self._fetchmaker('getUpdates')
        self.sendMessage = self._fetchmaker('sendMessage')
        
        self._listen_commands()

    def _fetchmaker(self, telegram_api_method):
        request = self._url + telegram_api_method
        fetch = self._client.fetch
        headers={'Content-Type': 'application/json'}

        def _fetcher(body):
            body = json.dumps(body)
            return fetch(
                request=request, body=body, method='POST', headers=headers)
        return _fetcher

    @gen.coroutine
    def _listen_commands(self):

        self._last_update = None
        update_body = {'timeout': 2}

        while True:
            latest = self._last_update
            # increase offset to filter out older updates
            update_body.update({'offset': latest+1} if latest else {})
            update_resp = self.getUpdates(update_body)
            update_resp.add_done_callback(self._respond_commands)
            yield gen.sleep(5)

    @gen.coroutine
    def _respond_commands(self, update_response):
        chatfile = self.chatfile
        chats = self.chats

        exc, upd = update_response.exception(), update_response.result().body
        if exc:
            LOGGER.error(str(exc))
        if not upd:
            return

        data = get_data(upd, self.bot_ident)
        for (update_id, chat_id, message_id, command) in data:
            self._last_update = update_id
            chat_is_known = (chat_id in chats)
            reply_text = None

            if command == '/activate':
                if chat_is_known:
                    reply_text = 'This chat is already activated.'
                else:
                    LOGGER.debug(
                            'Adding chat [%s] to notify list.', chat_id)
                    reply_text = 'Activated.'
                    chats.add(chat_id)
                    if chatfile:
                        write_to_file(chats, chatfile)

            elif command == '/deactivate':
                if chat_is_known:
                    LOGGER.debug(
                            'Deleting chat [%s] from notify list.', chat_id)
                    reply_text = 'Deactivated.'
                    chats.remove(chat_id)
                    if chatfile:
                        write_to_file(chats, chatfile)

            elif command == '/help':
                reply_text = HELP_MESSAGE

            else:
                LOGGER.warning(BOT_COMMAND_ERRORS[command])

            if reply_text:
                yield self.sendMessage({
                        'chat_id': chat_id,
                        'reply_to_message_id': message_id,
                        'text': reply_text,})

    @gen.coroutine
    def notify(self, level, *args, **kwargs):

        LOGGER.debug('Handler (%s) %s', self.name, level)

        notify_text = self.get_message(level, *args, **kwargs)
        for chat in self.chats:
            yield self.sendMessage({"chat_id": chat, "text": notify_text})

    def get_message(self, level, alert, value,
                    target=None, ntype=None, rule=None):

        msg_type = 'telegram' if ntype == 'graphite' else 'short'
        tmpl = TEMPLATES[ntype][msg_type]
        generated = tmpl.generate(
            level=level, reactor=self.reactor, alert=alert,
            value=value, target=target,)
        return generated.decode().strip()

def write_to_file(chats, chatfile):
    with open(chatfile, 'w') as fh:
        chats = map(str, chats)
        fh.write('\n'.join(chats))

def get_chatlist(chatfile):
    if not chatfile:
        return set()
    try:
        with open(chatfile) as fh:
            return set(int(chat) for chat in fh)
    except Exception as e:
        LOGGER.error('could not load saved chats:\n%s' % (e))
        return set()

def get_data(upd, bot_ident):
    update_content = json.loads(upd.decode())
    result = update_content['result']
    data = (get_fields(update, bot_ident) for update in result)
    return filter(None, data)

def get_fields(upd, bot_ident):
    """In telegram api, not every update has message field,
    and not every message has update field.
    We skip those cases. Rest of fields are mandatory.
    We also skip if text is not a valid command to handler.
    """
    msg = upd.get('message', {})
    text = msg.get('text')
    if not text:
        return
    chat_id  = msg['chat']['id']
    command = filter_commands(text, chat_id, bot_ident)
    if not command:
        return
    return (upd['update_id'], chat_id, msg['message_id'], command)

def filter_commands(text, chat_id, correct_ident):
    """Check if text is valid command to bot.
    Return string(either some command or error name) or None.
    Telegram group may have many participants including bots,
    so we need to check bot identifier to make sure command is
    given to our bot.
    """
    is_group = (chat_id < 0) # always negative for groups
    splitted = text.split()[:2]
    command = splitted[0].strip().lower()

    # make sure command is known
    if command not in ('/activate', '/deactivate', '/help'):
        return
    # dont check bot_ident if not in group
    if not is_group:
        return command
    # check bot_ident
    if len(splitted)<2:
        return 'no_ident'
    if splitted[1].strip() != correct_ident:
        return 'wrong_ident'
    
    return command
