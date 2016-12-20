"""Send alerts to telegram chats"""

import json
from os.path import exists

from tornado import gen, httpclient

from graphite_beacon.handlers import LOGGER, AbstractHandler
from graphite_beacon.template import TEMPLATES


HELP_MESSAGE = """Telegram handler for graphite-beacon
*usage* /command [parameters]
*examples*
/activate token123
/deactivate token123
*commands*
_activate_      activate bot and remember this chat
(no need to activate next time)
_deactivate_    deactivate bot and forget this chat
_help_          see this message
note: every command must be preceded by slash symbol (/)
*parameters*
_bot-ident_     mandatory for Telegram groups
note: parameters must be separated by whitespace
"""


class TelegramHandler(AbstractHandler):
    """uses telegram bot api to send alerts
    To make it work you want to:
    - create bot and write its token to configs:
    https://core.telegram.org/bots#3-how-do-i-create-a-bot
    - make up some bot_ident and write it to configs
    - optionally, make blank file for storing chats (chatfile)
    and write its path to configs
    """

    name = 'telegram'

    # Default options
    defaults = {
        'token': None,
        'bot_ident': None,
        'chatfile': None
    }

    def init_handler(self):

        token = self.options.get('token')
        assert token, 'Telegram bot API token is not defined.'

        self.client = CustomClient(token)

        self.bot_ident = self.options.get('bot_ident')
        assert self.bot_ident, 'Telegram bot ident token is not defined.'

        chatfile = self.options.get('chatfile')
        if not chatfile:
            LOGGER.warning('chatfile not found in configs')
        elif not exists(chatfile):
            LOGGER.error('chatfile specified in configs does not exist')
            chatfile = None
        self.chatfile = chatfile
        self.chats = get_chatlist(self.chatfile)

        self._listen_commands()

    @gen.coroutine
    def _listen_commands(self):
        """Monitor new updates and send them further to
        self._respond_commands, where bot actions
        are decided.
        """

        self._last_update = None
        update_body = {'timeout': 2}

        while True:
            latest = self._last_update
            # increase offset to filter out older updates
            update_body.update({'offset': latest + 1} if latest else {})
            update_resp = self.client.get_updates(update_body)
            update_resp.add_done_callback(self._respond_commands)
            yield gen.sleep(5)

    @gen.coroutine
    def _respond_commands(self, update_response):
        """Extract commands to bot from update and
        act accordingly. For description of commands,
        see HELP_MESSAGE variable on top of this module.
        """

        chatfile = self.chatfile
        chats = self.chats

        exc, upd = update_response.exception(), update_response.result().body
        if exc:
            LOGGER.error(str(exc))
        if not upd:
            return

        data = get_data(upd, self.bot_ident)
        for update_id, chat_id, message_id, command in data:
            self._last_update = update_id
            chat_is_known = chat_id in chats
            chats_changed = False
            reply_text = None

            if command == '/activate':
                if chat_is_known:
                    reply_text = 'This chat is already activated.'
                else:
                    LOGGER.debug(
                        'Adding chat [%s] to notify list.', chat_id)
                    reply_text = 'Activated.'
                    chats.add(chat_id)
                    chats_changed = True

            elif command == '/deactivate':
                if chat_is_known:
                    LOGGER.debug(
                        'Deleting chat [%s] from notify list.', chat_id)
                    reply_text = 'Deactivated.'
                    chats.remove(chat_id)
                    chats_changed = True

            if chats_changed and chatfile:
                write_to_file(chats, chatfile)

            elif command == '/help':
                reply_text = HELP_MESSAGE

            else:
                LOGGER.warning('Could not parse command: '
                               'bot ident is wrong or missing')

            if reply_text:
                yield self.client.send_message({
                    'chat_id': chat_id,
                    'reply_to_message_id': message_id,
                    'text': reply_text,
                    'parse_mode': 'Markdown',
                })

    @gen.coroutine
    def notify(self, level, *args, **kwargs):
        """Sends alerts to telegram chats.
        This method is called from top level module.
        Do not rename it.
        """

        LOGGER.debug('Handler (%s) %s', self.name, level)

        notify_text = self.get_message(level, *args, **kwargs)
        for chat in self.chats.copy():
            data = {"chat_id": chat, "text": notify_text}
            yield self.client.send_message(data)

    def get_message(self, level, alert, value, **kwargs):
        """Standart alert message. Same format across all
        graphite-beacon handlers.
        """
        target, ntype = kwargs.get('target'), kwargs.get('ntype')

        msg_type = 'telegram' if ntype == 'graphite' else 'short'
        tmpl = TEMPLATES[ntype][msg_type]
        generated = tmpl.generate(
            level=level, reactor=self.reactor, alert=alert,
            value=value, target=target,)
        return generated.decode().strip()


def write_to_file(chats, chatfile):
    """called every time chats are modified"""
    with open(chatfile, 'w') as handler:
        handler.write('\n'.join((str(id_) for id_ in chats)))


def get_chatlist(chatfile):
    """Try reading ids of saved chats from file.
    If we fail, return empty set"""
    if not chatfile:
        return set()
    try:
        with open(chatfile) as file_contents:
            return set(int(chat) for chat in file_contents)
    except (OSError, IOError) as exc:
        LOGGER.error('could not load saved chats:\n%s', exc)
        return set()


def get_data(upd, bot_ident):
    """Parse telegram update."""

    update_content = json.loads(upd.decode())
    result = update_content['result']
    data = (get_fields(update, bot_ident) for update in result)
    return (dt for dt in data if dt is not None)


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
    chat_id = msg['chat']['id']
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
    is_group = (chat_id < 0)  # always negative for groups
    split_cmd = text.split()[:2]
    command = split_cmd[0].strip().lower()

    # make sure command is known
    if command not in ('/activate', '/deactivate', '/help'):
        return
    # dont check bot_ident if not in group
    if not is_group:
        return command
    # check bot_ident
    if len(split_cmd) < 2:
        return 'no_ident'
    if split_cmd[1].strip() != correct_ident:
        return 'wrong_ident'

    return command


class CustomClient(object):
    """Handles all http requests using telegram api methods"""

    def __init__(self, tg_bot_token):
        self.token = tg_bot_token
        self.client = httpclient.AsyncHTTPClient()
        self.get_updates = self.fetchmaker('getUpdates')
        self.send_message = self.fetchmaker('sendMessage')

    def url(self, tg_api_method):
        """construct url from base url, bot token and api method"""
        base_url = 'https://api.telegram.org/bot%s/%s'
        return base_url % (self.token, tg_api_method)

    def fetchmaker(self, telegram_api_method):
        """Receives api method as string and returns
        wrapper around AsyncHTTPClient's fetch method
        """

        fetch = self.client.fetch
        request = self.url(telegram_api_method)

        def _fetcher(body, method='POST', headers=None):
            """Uses fetch method of tornado http client."""
            body = json.dumps(body)
            if not headers:
                headers = {}
            headers.update({'Content-Type': 'application/json'})
            return fetch(
                request=request, body=body, method=method, headers=headers)
        return _fetcher
