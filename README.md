graphite-beacon
===============

![logo](https://raw.github.com/klen/graphite-beacon/develop/beacon.png)

Simple alerting system for [Graphite](http://graphite.wikidot.com/) metrics.

Features:

- Simple installation
- No software dependencies (Databases, AMQP and etc)
- Light and fully asynchronous
- SMTP, HipChat, Slack, PagerDuty, HTTP handlers (PRs for additional handlers are welcome!)
- Easily configurable and supports historical values

[![Build status](http://img.shields.io/travis/klen/graphite-beacon.svg?style=flat-square)](http://travis-ci.org/klen/graphite-beacon)
[![Coverage](http://img.shields.io/coveralls/klen/graphite-beacon.svg?style=flat-square)](https://coveralls.io/r/klen/graphite-beacon)
[![Version](http://img.shields.io/pypi/v/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)
[![License](http://img.shields.io/pypi/l/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)
[![Downloads](http://img.shields.io/pypi/dm/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)

Example:
```js
{
"graphite_url": "http://g.server.org",
"smtp": {
    "from": "beacon@server.org",
    "to": ["me@gmail.com"]
},
"alerts": [
    {   "name": "MEM",
        "format": "bytes",
        "query": "aliasByNode(sumSeriesWithWildcards(collectd.*.memory.{memory-free,memory-cached}, 3), 1)",
        "rules": ["critical: < 200MB", "warning: < 400MB", "warning: < historical / 2"] },
    {   "name": "CPU",
        "format": "percent",
        "query": "aliasByNode(sumSeriesWithWildcards(collectd.*.cpu-*.cpu-user, 2), 1)",
        "rules": ["critical: >= 80%", "warning: >= 70%"] }
]}
```

Requirements
------------

- python (2.7, 3.3, 3.4)
- tornado
- funcparserlib
- pyyaml


Installation
------------

### Python package

**graphite-beacon** can be installed using pip:

    pip install graphite-beacon

### Debian package

Using the command line, add the following to your /etc/apt/sources.list system config file:

    echo "deb http://dl.bintray.com/klen/deb /" | sudo tee -a /etc/apt/sources.list
    echo "deb-src http://dl.bintray.com/klen/deb /" | sudo tee -a /etc/apt/sources.list

Install the package using apt-get:

    apt-get update
    apt-get install graphite-beacon

### Ansible role

There is an ansible role to install the package: https://github.com/Stouts/Stouts.graphite-beacon

## Docker

Build a config.json file and run :

    docker run -v /path/to/config.json:/srv/alerting/etc/config.json deliverous/graphite-beacon


Usage
-----

Just run `graphite-beacon`:

    $ graphite-beacon
    [I 141025 11:16:23 core:141] Read configuration
    [I 141025 11:16:23 core:55] Memory (10minute): init
    [I 141025 11:16:23 core:166] Loaded with options:
    ...

### Configuration

___

Time units:

> '2second', '3.5minute', '4hour', '5.2day', '6week', '7month', '8year'

> short formats are: '2s', '3m', '4.1h' ...

Value units:

> short: '2K', '3Mil', '4Bil', '5Tri'

> bytes: '2KB', '3MB', '4GB'

> bits: '2Kb', '3Mb', '4Gb'

> bps: '2Kbps', '3Mbps', '4Gbps'

> time: '2s', '3m', '4h', '5d'

The default options are:

> Note: comments are not allowed in JSON, but graphite-beacon strips them

```js

    {
        // Graphite server URL
        "graphite_url": "http://localhost",

        // Public graphite server URL
        // Used when notifying handlers, defaults to graphite_url
        "public_graphite_url": null,

        // HTTP AUTH username
        "auth_username": null,

        // HTTP AUTH password
        "auth_password": null,

        // Path to a pidfile
        "pidfile": null,

        // Default values format (none, bytes, s, ms, short)
        // Can be redefined for each alert.
        "format": "short",

        // Default query interval and time window when "time_window" is unset
        // Can be redefined for each alert.
        "interval": "10minute",

        // Default time window for Graphite queries
        // Defaults to query interval, can be redefined for each alert.
        "time_window": "10minute",

        // Notification repeat interval
        // If an alert is failed, its notification will be repeated with the interval below
        "repeat_interval": "2hour",

        // Default end time for Graphite queries
        // Defaults to the current time, can be redefined for each alert.
        "until": "0second",

        // Default loglevel
        "logging": "info",

        // Default method (average, last_value, sum, minimum, maximum).
        // Can be redefined for each alert.
        "method": "average",

        // Default alert to send when no data received (normal = no alert)
        // Can be redefined for each alert
        "no_data": "critical",

        // Default alert to send when loading failed (timeout, server error, etc)
        // (normal = no alert)
        // Can be redefined for each alert
        "loading_error": "critical"

        // Default prefix (used for notifications)
        "prefix": "[BEACON]",

        // Default handlers (log, smtp, hipchat, http, slack, pagerduty)
        "critical_handlers": ["log", "smtp"],
        "warning_handlers": ["log", "smtp"],
        "normal_handlers": ["log", "smtp"],

        // Send initial values (Send current values when reactor starts)
        "send_initial": true,

        // used together to ignore the missing value
        "default_nan_value": -1,
        "ignore_nan": false,

        // Default alerts (see configuration below)
        "alerts": [],

        // Path to other configuration files to include
        "include": []
    }
```

You can setup options with a configuration file. See examples for
[JSON](examples/example-config.json) and
[YAML](examples/example-config.yml).

A `config.json` file in the same directory that you run `graphite-beacon`
from will be used automatically.

#### Setup alerts

Currently two types of alerts are supported:
- Graphite alert (default) - check graphite metrics
- URL alert - load http and check status

> Note: comments are not allowed in JSON, but graphite-beacon strips them

```js

  "alerts": [
    {
      // (required) Alert name
      "name": "Memory",

      // (required) Alert query
      "query": "*.memory.memory-free",

      // (optional) Alert type (graphite, url)
      "source": "graphite",

      // (optional) Default values format (none, bytes, s, ms, short)
      "format": "bytes",

      // (optional) Alert method (average, last_value, sum, minimum, maximum)
      "method": "average",

      // (optional) Alert interval [eg. 15second, 30minute, 2hour, 1day, 3month, 1year]
      "interval": "1minute",

      // (optional) What kind of alert to send when no data received (normal = no alert)
      "no_data": "warning",

      // (optional) Alert interval end time (see "Alert interval" for examples)
      "until": "5second",

      // (required) Alert rules
      // Rule format: "{level}: {operator} {value}"
      // Level one of [critical, warning, normal]
      // Operator one of [>, <, >=, <=, ==, !=]
      // Value (absolute value: 3000000 or short form like 3MB/12minute)
      // Multiple conditions can be separated by AND or OR conditions
      "rules": [ "critical: < 200MB", "warning: < 300MB" ]
    }
  ]
```

##### Historical values

graphite-beacon supports "historical" values for a rule.
For example you may want to get warning when CPU usage is greater than 150% of normal usage:

    "warning: > historical * 1.5"

Or memory is less than half the usual value:

    "warning: < historical / 2"


Historical values for each query are kept. A historical value
represents the average of all values in history. Rules using a historical value will
only work after enough values have been collected (see `history_size`).

History values are kept for 1 day by default. You can change this with the `history_size`
option.

See the below example for how to send a warning when today's new user count is
less than 80% of the last 10 day average:

```js
alerts: [
  {
    "name": "Registrations",
    // Run once per day
    "interval": "1day",
    "query": "Your graphite query here",
    // Get average for last 10 days
    "history_size": "10day",
    "rules": [
      // Warning if today's new user less than 80% of average for 10 days
      "warning: < historical * 0.8",
     // Critical if today's new user less than 50% of average for 10 days
      "critical: < historical * 0.5"
    ]
  }
],
```

### Handlers

Handlers allow for notifying an external service or process of an alert firing.

#### Email Handler

Sends an email (enabled by default).

```js
{
    // SMTP default options
    "smtp": {
        "from": "beacon@graphite",
        "to": [],                   // List of email addresses to send to
        "host": "localhost",        // SMTP host
        "port": 25,                 // SMTP port
        "username": null,           // SMTP user (optional)
        "password": null,           // SMTP password (optional)
        "use_tls": false,           // Use TLS?
        "html": true,               // Send HTML emails?

        // Graphite link for emails (By default is equal to main graphite_url)
        "graphite_url": null
    }
}
```

#### HipChat Handler

Sends a message to a HipChat room.

```js
{
    "hipchat": {
        // (optional) Custom HipChat URL
        "url": 'https://api.custom.hipchat.my',

        "room": "myroom",
        "key": "mykey"
    }
}
```

#### Webhook Handler (HTTP)

Triggers a webhook.

```js
{
    "http": {
        "url": "http://myhook.com",
        "params": {},                 // (optional) Additional query(data) params
        "method": "GET"               // (optional) HTTP method
    }
}
```

#### Slack Handler

Sends a message to a user or channel on Slack.

```js
{
    "slack": {
        "webhook": "https://hooks.slack.com/services/...",
        "channel": "#general",          // #channel or @user (optional)
        "username": "graphite-beacon",
    }
}
```

#### Command Line Handler

Runs a command.

```js
{
    "cli": {
        // Command to run (required)
        // Several variables that will be substituted by values are allowed:
        //  ${level} -- alert level
        //  ${name} -- alert name
        //  ${value} -- current metrics value
        //  ${limit_value} -- metrics limit value
        "command": "./myscript ${level} ${name} ${value} ...",

        // Whitelist of alerts that will trigger this handler (optional)
        // All alerts will trigger this handler if absent.
        "alerts_whitelist": ["..."]
    }
}
```

#### PagerDuty Handler

Triggers a PagerDuty incident.

```js
{
    "pagerduty": {
        "subdomain": "yoursubdomain",
        "apitoken": "apitoken",
        "service_key": "servicekey",
    }
}
```

#### Telegram Handler

Sends a Telegram message.

```js
{
    "telegram": {
        "token": "telegram bot token",
        "bot_ident": "token you choose to activate bot in a group"
        "chatfile": "path to file where chat ids are saved, optional field"
    }
}
```

### Command Line Usage

```
  $ graphite-beacon --help
  Usage: graphite-beacon [OPTIONS]

  Options:

    --config                         Path to an configuration file (JSON/YAML)
                                     (default config.json)
    --graphite_url                   Graphite URL (default http://localhost)
    --help                           show this help information
    --pidfile                        Set pid file

    --log_file_max_size              max size of log files before rollover
                                     (default 100000000)
    --log_file_num_backups           number of log files to keep (default 10)
    --log_file_prefix=PATH           Path prefix for log files. Note that if you
                                     are running multiple tornado processes,
                                     log_file_prefix must be different for each
                                     of them (e.g. include the port number)
    --log_to_stderr                  Send log output to stderr (colorized if
                                     possible). By default use stderr if
                                     --log_file_prefix is not set and no other
                                     logging is configured.
    --logging=debug|info|warning|error|none
                                     Set the Python log level. If 'none', tornado
                                     won't touch the logging configuration.
                                     (default info)
```

Bug tracker
-----------

If you have any suggestions, bug reports or annoyances please report them to
the issue tracker at https://github.com/klen/graphite-beacon/issues

Contributors
-------------

* Andrej Kuročenko (https://github.com/kurochenko)
* Cody Soyland (https://github.com/codysoyland)
* Garrett Heel (https://github.com/GarrettHeel)
* George Ionita (https://github.com/georgeionita)
* James Yuzawa (https://github.com/yuzawa-san)
* Kirill Klenov (https://github.com/klen)
* Konstantin Bakulin (https://github.com/kbakulin)
* Lammert Hellinga (https://github.com/Kogelvis)
* Miguel Moll (https://github.com/MiguelMoll)
* Nick Pillitteri (https://github.com/56quarters)
* Niku Toivola (https://github.com/nikut)
* Olli-Pekka Puolitaival (https://github.com/OPpuolitaival)
* Phillip Hagedorn (https://github.com/phagedorn)
* Raine Virta (https://github.com/raine)
* Scott Nonnenberg (https://github.com/scottnonnenberg)
* Sean Johnson (https://github.com/pirogoeth)
* Terry Peng (https://github.com/tpeng)
* Thomas Clavier (https://github.com/tclavier)
* Yuriy Ilyin (https://github.com/YuriyIlyin)
* dugeem (https://github.com/dugeem)
* Joakim (https://github.com/VibyJocke)

License
--------

Licensed under a [MIT license](http://www.linfo.org/mitlicense.html)

If you wish to express your appreciation for the role, you are welcome to send
a postcard to:

    Kirill Klenov
    pos. Severny 8-3
    MO, Istra, 143500
    Russia
