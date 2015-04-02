graphite-beacon
===============

![logo](https://raw.github.com/klen/graphite-beacon/develop/beacon.png)

Simple alerting system for [Graphite](http://graphite.wikidot.com/) metrics.

Features:

- Simplest installation (one python package dependency);
- No software dependencies (Databases, AMQP and etc);
- Light and full asyncronous;
- SMTP, Hipchat, Slack, HTTP handlers (Please make a request for additional handlers);
- Easy configurable and support "historical values"

[![Build status](http://img.shields.io/travis/klen/graphite-beacon.svg?style=flat-square)](http://travis-ci.org/klen/graphite-beacon)
[![Coverage](http://img.shields.io/coveralls/klen/graphite-beacon.svg?style=flat-square)](https://coveralls.io/r/klen/graphite-beacon)
[![Version](http://img.shields.io/pypi/v/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)
[![License](http://img.shields.io/pypi/l/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)
[![Downloads](http://img.shields.io/pypi/dm/graphite-beacon.svg?style=flat-square)](https://pypi.python.org/pypi/graphite_beacon)
[![Donate](http://img.shields.io/gratipay/klen.svg?style=flat-square)](https://www.gratipay.com/klen/)

Example:
```js
{
"graphite_url": "http://g.server.org"
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
        "rules": ["critical: >= 80%", "warning: >= 70%"] },
]}
```

Requirements
------------

- python (2.6, 2.7, 3.3, 3.4)
- tornado


Installation
------------

### Python package

**Graphite-beacon** could be installed using pip:

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

    docker run -v /path/to/config.json:/config.json deliverous/graphite-beacon


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

**Graphite-beacon** default options are:

> Comment lines are not allowed in JSON, but Graphite-beacon strips them

```js

    {
        // Path to a configuration
        "config": "config.json",

        // Graphite server URL
        "graphite_url": "http://localhost",

        // HTTP AUTH username
        "auth_usernamename": null,

        // HTTP AUTH password
        "auth_password": null,

        // Path to a pidfile
        "pidfile": null,

        // Default values format (none, bytes, s, ms, short)
        // Can be redfined for each alert.
        "format": "short",

        // Default query interval
        // Can be redfined for each alert.
        "interval": "10minute",

        // Default time window for Graphite queries
        // Defaults to query interval, can be redefined for each alert.
        "time_window": "10minute",

        // Notification repeat interval
        // If an alert is failed, its notification will be repeated with the interval below
        "repeat_interval": "2hour",

        // Default loglevel
        "logging": "info",

        // Default method (average, last_value, sum).
        // Can be redfined for each alert.
        "method": "average",

        // Default prefix (used for notifications)
        "prefix": "[BEACON]",

        // Default handlers (log, smtp, hipchat, http, slack)
        "critical_handlers": ["log", "smtp"],
        "warning_handlers": ["log", "smtp"],
        "normal_handlers": ["log", "smtp"],

        // Send initial values (Send current values when reactor starts)
        "send_initial": true,

        // Default alerts (see configuration below)
        "alerts": []
    }
```

You can setup options with a configuration file. See
`example-config.json`.

#### Include

You can include any configuration files:
```js
...
"include": [ "path/to/config1.json", "path/to/config2.json"]
```

#### Setup alerts

At the moment **Graphite-beacon** supports two type of alerts:
- Graphite alert (default) - check graphite metrics
- URL alert (default) - load http and check status

> Comment lines are not allowed in JSON, but Graphite-beacon strips them

```js

  "alerts": [
    {
      // (required) Alert name
      "name": "Memory",

      // (required) Alert query
      "query": "*.memory.memory-free",

      //(optional) Alert type (graphite, url)
      "source": "graphite",

      //(optional)  Default values format (none, bytes, s, ms, short)
      "format": "bytes",

      // (optional) Alert method (average, last_value, sum)
      "method": "average",

      // (optional) Alert interval [eg. 15second, 30minute, 2hour, 1day, 3month, 1year]
      "interval": "1minute",

      // (required) Alert rules
      // Rule format: "{level}: {operator} {value}"
      // Level one of [critical, warning, normal]
      // Operator one of [>, <, >=, <=, ==, !=]
      // Value (absolute value: 3000000 or short form like 3MB/12minute)
      "rules": [ "critical: < 200MB", "warning: < 300MB" ]
    }
  ]
```

##### Historical values

Graphite-beacon supports "historical" values for a rule.
By example, you want to get warning when CPU usage is more than 150% from normal usage:

    "warning: > historical * 1.5"

Or memory is twice less than usual:

    "warning: < historical / 2"


Graphite-beacon keeps history of values for each target in metric. Historical value
is average of values from history. "Historical" rule becames work when it has enough
values (Read about history size bellow).

History values are keeping 1 day by default. You can change it by using Reactor option
'history_size'.

By example, send warning when today' new user is less than 80% of average for last 10 days:

```js
...
alerts: [
...
{
  "name": "Registrations",
  // Run once per day
  "interval": "1day",
  "query": "Your graphite query here",
  // Get average for last 10 days
  "history_size": 10day,
  "rules": [
    // Warning if today's new user less than 80% of average for 10 days
    "warning: < historical * 0.8",
   // Critical if today's new user less than 50% of average for 10 days
    "critical: < historical * 0.5"
  ]
}
...
],
...
```

### Setup SMTP

Enable "smtp" handler (enabled by default) and set the options in your beacon
configuration.

```js
{
    ...
    // SMTP default options
    "smtp": {

        // Set from email
        "from": "beacon@graphite",

        // Set "to" email
        "to": [],

        // Set SMTP host
        "host": "localhost",

        // Set SMTP port
        "port": 25,

        // Set SMTP user
        "username": null,

        // Set SMTP password
        "password": null,

        // Use TLS
        "use_tls": false,

        // Send HTML emails
        "html": true,

        // Graphite link for emails (By default is equal to main graphite_url)
        "graphite_url": null

    }

    ...
}
```

### Setup HipChat

Enable "hipchat" handler and set the options in your beacon configuration.

```js
{
    ...
    "hipchat": {
        // (optional) Custom HipChat URL
        "url": 'https://api.custom.hipchat.my',

        "room": "myroom",
        "key": "mykey"
    }
    ...
}
```

### Setup HttpHandler

Enable "http" handler and set the options in your beacon configuration.

```js
{
    ...
    "http": {
        "url": "http://myhook.com",

        // (optional) Additional query(data) params
        "params": {},

        // (optional) HTTP method
        "method": "GET"

    }
    ...
}
```

### Setup SlackHandler

Enable "slack" handler and set the options in your beacon configuration.

```js
{
    ...
    "slack": {
        "webhook": "http://myhook.com",
        // optional
        "channel": "#general",
        // optional
        "username": "graphite-beacon",
    }
    ...
}
```

### Setup CliHandler

Enable handler for running command line commands and set the options in your beacon configuration.

```js
{
    ...
    "cli": {
        // Several variables that will be substituted by values are allowed in configuration
        // ${level} -- alert level
        // ${name} -- alert name
        // ${value} -- current metrics value
        // ${limit_value} -- metrics limit value
        // required
        "command": "./myscript ${level} ${name} ${value} ...",
        // optional -- if present only alerts with specified names will trigger this handler. If not present, all alerts will trigger handler
        "alerts_whitelist": ["..."]
    }
    ...
}
```

### Command line

```
  $ graphite-beacon --help
  Usage: graphite-beacon [OPTIONS]

  Options:

    --config                         Path to an configuration file (YAML)
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

* Kirill Klenov     (https://github.com/klen, horneds@gmail.com)

* Andrej Kuročenko (https://github.com/kurochenko)
* Cody Soyland (https://github.com/codysoyland)
* George Ionita (https://github.com/georgeionita)
* James Yuzawa (https://github.com/yuzawa-san)
* Nick Pillitteri (https://github.com/56quarters)
* Niku Toivola (https://github.com/nikut)
* Raine Virta (https://github.com/raine)
* Thomas Clavier (https://github.com/tclavier)
* dugeem (https://github.com/dugeem)

License
--------

Licensed under a [MIT license](http://www.linfo.org/mitlicense.html)
