## Unreleased

- Bug fix: Include pyyaml by default and use YAML config loader for `.yaml` files (#143)

## 0.26.0

- Improvement: use `validate_cert` for URL alerts (#111)
- Improvement: better incident key and `client_url` for pagerduty handler (#109)
- Improvement/bug fixes: enable persistence for the telegram handler and various bug fixes (#130)

## 0.25.4

- Bug fix: don't crash due to lack of SIGHUP on Windows (#94)
- Bug fix: access dict correctly in hipchat handler (#96)
- Improvement: Allow slack notifications to users (#100)

## 0.25.3

- Added 'minimum' and 'maximum' methods
- Allow alerts to be defined in multiple config files

## 0.25.1

- Fix issue #46;
- Support `until` option for Graphite queries;
- Customize alert behaviour with no data;
- Enhance expressions (support AND/OR);
- Added VictorOps handler;
- Better Slack notifications;
- Added `public_graphite_url` option;

## 0.24.0

- Support YAML in config files.
  You should have install `yaml` and use `<filename>.yml` as config files.

## 0.23.0

- Support systemd
- Update CLI handler
- Add PagerDuty handler

## 0.20.0

- Add Slack (https://slack.com) handler
- Add `request_timeout` alerts' option
- Change history_size format: 144 -> 1day

## 0.18.0

- Python 2.6 support

## 0.14.0

- Add `smtp.graphite_url` option for set graphite_url in emails
- Add `send_initial` option for send initial values when graphite-beacon starts
- Update HTML email templates

## 0.12.0

- Change format of handlers options

## 0.11.0

- Fix release 0.9.0

## 0.9.0

- Update units system
- Support `include`
- Easiest rules format

## 0.6.1

- Support units format (bytes, s, ms, short, percent)
- HTML emails
- Added `repeat_interval`

## 0.4.0

- Support URL alerts (load http response and check status)

## 0.2.0

- First public release
