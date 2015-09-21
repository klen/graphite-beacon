import json
from tornado import gen, httpclient

from graphite_beacon.handlers import AbstractHandler, LOGGER
from graphite_beacon.template import TEMPLATES


class TelegramHandler(AbstractHandler):

    name = 'telegram'

    # Default options
    defaults = {
        'token': None,
        'bot_ident': None
    }

    def init_handler(self):

        self.token = self.options.get('token')
        assert self.token, 'Telegram bot API token is not defined.'

        self.bot_ident = self.options.get('bot_ident')
        assert self.bot_ident, 'Telegram bot ident token is not defined.'

        self.client = httpclient.AsyncHTTPClient()
        self.url = "https://api.telegram.org/bot%s/" % (self.token)

        self._chats = []
        self._listen_commands()

    def get_message(self, level, alert, value, target=None, ntype=None, rule=None):

        msg_type = 'telegram' if ntype == 'graphite' else 'short'
        tmpl = TEMPLATES[ntype][msg_type]
        return tmpl.generate(
            level=level, reactor=self.reactor, alert=alert, value=value, target=target).strip()

    @gen.coroutine
    def _listen_commands(self):

        self._last_update = None

        update_body = {"timeout": 2}

        update_headers = {"Content-Type": "application/json"}

        while True:
            if self._last_update:
                update_body.update({"offset": self._last_update + 1})
            update_resp = self.client.fetch(
                self.url + "getUpdates", headers=update_headers,
                body=json.dumps(update_body), method="POST")
            update_resp.add_done_callback(self._respond_commands)
            yield gen.sleep(5)

    @gen.coroutine
    def _respond_commands(self, update_response):

        if update_response.exception():
            LOGGER.error(str(update_response.exception()))

        update_content = update_response.result().body
        if not update_content:
            return
        else:
            update_content = json.loads(update_content)

        for update in update_content["result"]:
            if not update["message"].get('text'):
                continue
            message = update["message"]["text"].encode("utf-8")
            msp = message.split()
            self._last_update = update["update_id"]
            if len(msp) > 1 and msp[0].startswith("/activate"):
                try:
                    chat_id = update["message"]["chat"]["id"]
                    if msp[1] == self.bot_ident and chat_id not in self._chats:
                        LOGGER.debug(
                            "Adding chat [%s] to notify list.", chat_id)
                        self._chats.append(chat_id)
                        yield self.client.fetch(
                            self.url + "sendMessage", body=json.dumps({
                                "chat_id": update["message"]["chat"]["id"],
                                "reply_to_message_id": update["message"]["message_id"],
                                "text": "Activated!"}),
                            method="POST",
                            headers={"Content-Type": "application/json"})
                    elif msp[1] == self.bot_ident and chat_id in self._chats:
                        yield self.client.fetch(
                            self.url + "sendMessage", body=json.dumps({
                                "chat_id": update["message"]["chat"]["id"],
                                "reply_to_message_id": update["message"]["message_id"],
                                "text": "This chat is already activated."}),
                            method="POST",
                            headers={"Content-Type": "application/json"})
                except:
                    continue
            else:
                continue

    @gen.coroutine
    def notify(self, level, *args, **kwargs):

        LOGGER.debug("Handler (%s) %s", self.name, level)

        message = self.get_message(level, *args, **kwargs)
        for chat in self._chats:
            yield self.client.fetch(
                self.url + "sendMessage", body=json.dumps({"chat_id": chat, "text": message}),
                method="POST", headers={"Content-Type": "application/json"})
