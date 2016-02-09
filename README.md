# synapse
Distributed Computing Framework

# Builds

## Travis-Ci ( Linux: py-2.7 / py-3.4 )
[![Build Status](https://travis-ci.org/vivisect/synapse.svg)](https://travis-ci.org/vivisect/synapse)

## AppVeyor ( Windows: py-2.7 / py-3.4 )
[![Build Status](https://ci.appveyor.com/api/projects/status/github/vivisect/synapse?branch=master&svg=true)](https://ci.appveyor.com/project/invisig0th/synapse/)

# Components

## eventbus

## telepath

## mindmeld

## hivemind

# Tools

## python -m synapse.tools.dmon

Synapse.tools.dmon is a multi-purpose tool for running a synapse daemon and
sharing objects.  It allows objects to be created and shared, optionally using
a service bus, by config options in a json file rather than requiring custom
code for each intended service.

### example configs

Config dictionaries may be stored as JSON files or passed in programatically.
The following examples use JSON syntax and could be loaded from a file.

The following config shares a ram:/// cortex as the object "foo" and listens
via both the local socket "mysock" and tcp loopback on port 3344.

```
{
    "ctors":[
        ["foo","ctor:///synapse.cortex.openurl('ram:///')"]
    ],

    "dmon:share":[
        [ "foo", {} ]
    ],

    "dmon:listen":[
        "local://mysock/",
        "tcp://127.0.0.1:3344"
    ]
}
```

# Libs

