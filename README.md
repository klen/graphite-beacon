|logo| graphite-beacon
======================

Simple allerting system for Graphite\_ metrics.

Features:

-   Simplest installation (one python package dependency);
-   No software dependencies (Databases, AMPQ and etc);
-   Light and full asyncronous;
-   SMTP, Hipchat handlers (Please make a request for additional
    handlers);

[![Build Status][]][]

[![Coverals][]][]

[![Donate][]][]

Requirements
------------

- python (2.7, 3.3, 3.4)
- tornado \>= 4.0.0

Installation
------------

**Graphite-beacon** could be installed using pip: :

    pip intall graphite-beacon

Usage
-----

Just run \`graphite-beacon\`:

    $ graphite-beacon
    [I 141025 11:16:23 core:141] Read configuration
    [I 141025 11:16:23 core:55] Memory (10minute): init
    [I 141025 11:16:23 core:166] Loaded with options:
    ...

### Configuration

**Graphite-beacon** default options are:

> **note**
>
> Comment lines are not allowed in real JSON!

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

You can setup options with a configuration file. See
example-config.json.

### Setup alerts

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
            "operator": "

  [Build Status]: http://img.shields.io/travis/klen/graphite-beacon.svg?style=flat-square
  [![Build Status][]]: http://travis-ci.org/klen/graphite-beacon
  [Coverals]: http://img.shields.io/coverals/klen/graphite-beacon.svg?style=flat-square
  [![Coverals][]]: https://coveralls.io/r/klen/graphite-beacon
  [Donate]: http://img.shields.io/gratipay/klen.svg?style=flat-square
  [![Donate][]]: https://www.gratipay.com/klen/
