import os.path as op

from tornado import template

LOADER = template.Loader(op.join(op.dirname(op.abspath(__file__)), 'templates'), autoescape=None)
TEMPLATES = {
    'graphite': {
        'html': LOADER.load('graphite/message.html'),
        'text': LOADER.load('graphite/message.txt'),
        'short': LOADER.load('graphite/short.txt'),
        'telegram': LOADER.load('graphite/short.txt'),
        'slack': LOADER.load('graphite/slack.txt')
    },
    'url': {
        'html': LOADER.load('url/message.html'),
        'text': LOADER.load('url/message.txt'),
        'short': LOADER.load('url/short.txt'),
    },
    'common': {
        'html': LOADER.load('common/message.html'),
        'text': LOADER.load('common/message.txt'),
        'short': LOADER.load('common/short.txt'),
    },
}
