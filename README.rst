|logo| graphite-beacon
######################

.. _description:

Simple allerting system for Graphite_ metrics.

Features:

* Simplest installation (one python package dependency);
* No software dependencies (Databases, AMPQ and etc);
* Light and full asyncronous;
* SMTP, Hipchat handlers (Please make a request for additional handlers);

.. _badges:

.. image:: https://secure.travis-ci.org/klen/mixer.png?branch=develop
    :target: http://travis-ci.org/klen/mixer
    :alt: Build Status

.. image:: https://coveralls.io/repos/klen/mixer/badge.png?branch=develop
    :target: https://coveralls.io/r/klen/mixer
    :alt: Coverals

.. image:: https://dl.dropboxusercontent.com/u/487440/reformal/donate.png
    :target: https://www.gittip.com/klen/
    :alt: Donate

.. _contents:

.. contents::

.. _requirements:

Requirements
=============

- python (2.7, 3.3, 3.4)
- tornado >= 4.0.0

.. _installation:

Installation
=============

**Graphite-beacon** could be installed using pip: ::

    pip intall graphite-beacon

.. _usage:

Usage
=====
Just run `graphite-beacon`::

::
    $ graphite-beacon
    [I 141025 11:16:23 core:141] Read configuration
    [I 141025 11:16:23 core:55] Memory (10minute): init
    [I 141025 11:16:23 core:166] Loaded with options:
    ...

.. _configuration:

Configuration
-------------

**Graphite-beacon** default options are:

.. note:: Comment lines are not allowed in real JSON!

::

    {
        // Path to a configuration
        "config": "config.json",

        // Graphite server URL
        "graphite_url": "http://localhost",

        // HTTP AUTH username
        "graphite_user": null,

        // HTTP AUTH password
        "graphite_password": null,

        // Path to a pidfile
        "pidfile": null,

        // Default query interval
        // Can be redfined for each alert.
        "interval": "10minute",

        // Default loglevel
        "logging": "info",

        // Default method (average, last_value).
        // Can be redfined for each alert.
        "method": "average",

        // Default prefix (used for notifications)
        "prefix": "[BEACON]",

        // Default handlers (log, smtp, hipchat)
        "critical_handlers": ["log", "smtp"],
        "warning_handlers": ["log", "smtp"],
        "normal_handlers": ["log", "smtp"],

        // Default alerts (see configuration below)
        "alerts": []
    }

You can setup options with a configuration file. See `example-config.json`.

Setup alerts
------------
::

  "alerts": [
    {
      // Alert name (required)
      "name": "Memory",

      // Alert query (required)
      "query": "*.memory.memory-free",

      // Alert method (optional)
      "method": "average",

      // Alert interval (optional)
      "interval": "1minute",

      // Alert rules
      "rules": [
        {
          // Level
          "level": "critical",
          // Conditional (gt (>), ge (>=), lt (<), le (<=), eq (==))
          "operator": "gt",

          // Value to compare
          "value": 80
        },
        {
          "level": "warning",
          "operator": "gt",
          "value": 60
        }
      ]
    }
  ]

.. _command-line:

Command line
------------

::

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

.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them to
the issue tracker at https://github.com/klen/graphite-beacon/issues

.. _contributors:

Contributors
=============

* Kirill Klenov     (https://github.com/klen, horneds@gmail.com)

.. _license:

License
=======

Licensed under a `MIT license`_.

.. _links:

.. _Graphite: http://graphite.wikidot.com/
.. _BSD license: http://www.linfo.org/mitlicense.html
.. |logo| image:: https://raw.github.com/klen/graphite-beacon/develop/beacon.jpg
                  :width: 100
