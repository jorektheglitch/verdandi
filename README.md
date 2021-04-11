# Verdandi

Verdandi is a simple GUI for the Yggdrasil admin API. It allows you to view information about your running Yggdrasil node.

At this time, only read operations are supported. Things like adding peers or changing your Yggdrasil configuration are currently out of scope. Contributions are very welcome, though!

## Installation

In order to run Verdandi, you must install [tkinter](https://docs.python.org/3/library/tkinter.html) for your platform.

## Running

Once you have installed tkinter, you can run Verdandi with the following command:

```
python ./verdandi.py
```

**Note:** You may have to run Verdandi as root, especially if your Yggdrasil admin API is configured to listed on a UNIX socket.

## Troubleshooting Links

[tkinter.TclError: couldn't connect to display ...](https://stackoverflow.com/a/59011769)
