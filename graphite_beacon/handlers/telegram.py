import json
from tornado import gen, httpclient

from graphite_beacon.handlers import AbstractHandler, LOGGER
from graphite_beacon.template import TEMPLATES

NO_CHATFILE = (
    'chatfile not found in configs. If you want telegram handler to '
    'persist chats and groups in which you activate bot after '
    'graphite-beacon is restarted, create blank text file and write '
    'it`s path to chatfile field in your config file.')

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

        self.chatfile = self.options.get('chatfile')
        if not self.chatfile: LOGGER.warning(NO_CHATFILE)

        self.client = httpclient.AsyncHTTPClient()
        self.url = 'https://api.telegram.org/bot%s/' % (self.token)

        self._chats = self._get_chatlist()
        self._listen_commands()

    @gen.coroutine
    def _listen_commands(self):

        self._last_update = None

        update_body = {"timeout": 2}

        while True:

            if self._last_update:
                update_body.update({"offset": self._last_update + 1})

            req = self._prepare_request('getUpdates', update_body)
            update_resp = self.client.fetch(**req)

            update_resp.add_done_callback(self._respond_commands)
            yield gen.sleep(5)

    @gen.coroutine
    def _respond_commands(self, update_response):
        chatfile = self.chatfile

        if update_response.exception():
            LOGGER.error(str(update_response.exception()))

        upd = update_response.result().body
        if not upd:
            return

        update_content = json.loads(upd.decode())
        for update in update_content['result']:

            update_id = update.get('update_id')
            if not update_id: continue

            message = update.get('message')  # fix key error here
            if not message: continue

            text = message.get('text')
            if not text: continue

            message_id = message.get('message_id')
            if not message_id: continue

            chat_id = message.get('chat', {}).get('id')
            if not chat_id: continue

            if not self._correct_activation(text, chat_id):
                continue

            self._last_update = update_id

            if chat_id not in self._chats:
                reply_text = 'Activated!'

                LOGGER.debug('Adding chat [%s] to notify list'
                                % (chat_id))
                self._chats.append(int(chat_id))

                if chatfile:
                    LOGGER.debug('Writing chat [%s] to file %s'
                                    % (chat_id, chatfile))
                    self._save_to_file(chat_id, chatfile)

            else:
                reply_text = 'This chat is already activated'

            response_body = {
                "chat_id": chat_id,
                "reply_to_message_id": message_id,
                "text": reply_text}

            bot_response = self._prepare_request('sendMessage', response_body)
            yield self.client.fetch(**bot_response)

    @gen.coroutine
    def notify(self, level, *args, **kwargs):
        request_url = self.url + 'sendMessage'

        LOGGER.debug('Handler (%s) %s', self.name, level)

        notify_text = self.get_message(level, *args, **kwargs)
        for chat in self._chats:

            body = {"chat_id": chat, "text": notify_text}
            notification = self._prepare_request('sendMessage', body)

            yield self.client.fetch(**notification)

    def _get_chatlist(self):
        try:
            with open(self.chatfile) as fh:
                return [int(chat) for chat in fh]
        except Exception as e:
            LOGGER.debug('could not load saved chats:\n%s' % (e))
            return []

    def _prepare_request(self, target, body, method='POST',
                            headers={"Content-Type": "application/json"}):

        return dict(request=self.url + target, body=json.dumps(body),
                    method=method, headers=headers,)

    def _correct_activation(self, text, chat_id):
        """Helper method, called from _respond_commands
        when bot gets message from user.
        If chat_id is positive, we don't call bot from group
        or channel so there is no need to check bot_ident.
        """
        splitted = text.split()
        init = splitted[0].strip().lower()
        init_iscorrect = init.startswith(r'/activate')

        if int(chat_id) > 0:
            return init_iscorrect

        elif len(splitted) >= 2:
            bot_id = splitted[1].strip()
            bot_id_iscorrect = bot_id.startswith(self.bot_ident)
            return (init_iscorrect and bot_id_iscorrect)

        else:
            return False

    def _save_to_file(self, chat_id, chatfile):
        with open(chatfile, 'a') as fh:
            fh.write('%s\n' % (chat_id))

    def get_message(self, level, alert, value,
                    target=None, ntype=None, rule=None):

        msg_type = 'telegram' if ntype == 'graphite' else 'short'
        tmpl = TEMPLATES[ntype][msg_type]
        generated = tmpl.generate(
            level=level, reactor=self.reactor, alert=alert,
            value=value, target=target,)
        return generated.decode().strip()
