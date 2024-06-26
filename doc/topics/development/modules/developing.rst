======================
Developing New Modules
======================

Interactive Debugging
=====================

Sometimes debugging with ``print()`` and extra logs sprinkled everywhere is not
the best strategy.

IPython is a helpful debug tool that has an interactive python environment
which can be embedded in python programs.

First the system will require IPython to be installed.

.. code-block:: bash

    # Debian
    apt-get install ipython

    # Arch Linux
    pacman -Syu ipython2

    # RHEL/CentOS (via EPEL)
    yum install python-ipython


Now, in the troubling python module, add the following line at a location where
the debugger should be started:

.. code-block:: python

    test = "test123"
    import IPython

    IPython.embed_kernel()

After running a Salt command that hits that line, the following will show up in
the log file:

.. code-block:: text

    [CRITICAL] To connect another client to this kernel, use:
    [IPKernelApp] --existing kernel-31271.json

Now on the system that invoked ``embed_kernel``, run the following command from
a shell:

.. code-block:: bash

    # NOTE: use ipython2 instead of ipython for Arch Linux
    ipython console --existing

This provides a console that has access to all the vars and functions, and even
supports tab-completion.

.. code-block:: python

    print(test)
    test123

To exit IPython and continue running Salt, press ``Ctrl-d`` to logout.

.. _loader:

The Salt Loader
===============

Salt's loader system is responsible for reading `Special Module Contents`_ and
providing the context for the special `Dunder Dictionaries`_. When modules
developed for Salt's loader are imported directly, the dunder attributes won't
be populated. You can use the `Loader Context`_ to work around this.

Loader Context
--------------

Given the following.

.. code-block:: python

        # coolmod.py


        def utils_func_getter(name):
            return __utils__[name]

You would not be able import ``coolmod`` and run ``utils_func_getter`` because
``__utils__`` would not be defined. You must run ``coolmod.utils_func_getter``
in the context of a loader.

.. code-block:: python

        import coolmod
        import salt.loader

        opts = {}
        utils = salt.loader.utils(opts)
        with salt.loader.context(utils):
            func = coolmod.utils_func_getter("foo.bar")



Special Module Contents
=======================

These are things that may be defined by the module to influence various things.

__virtual__
-----------

__virtual_aliases__
-------------------

__virtualname__
---------------

__init__
--------

Called before ``__virtual__()``

__proxyenabled__
----------------
grains and proxy modules

__proxyenabled__ as a list containing the names of the proxy types that the module supports.

__load__
--------

__func_alias__
--------------

__outputter__
-------------

.. _dunder-dictionaries:

Dunder Dictionaries
===================

Salt provides several special "dunder" dictionaries as a convenience for Salt
development.  These include ``__opts__``, ``__context__``, ``__salt__``, and
others. This document will describe each dictionary and detail where they exist
and what information and/or functionality they provide.

The following dunder dictionaries are always defined, but may be empty

* ``__context__``
* ``__grains__``
* ``__pillar__``
* ``__opts__``


__opts__
--------

.. versionchanged:: 3006.0

    The ``__opts__`` dictionary can now be accessed via
    :py:mod:`~salt.loader.context``.

Defined in: All modules

The ``__opts__`` dictionary contains all of the options passed in the
configuration file for the master or minion.

.. note::

    In many places in salt, instead of pulling raw data from the __opts__
    dict, configuration data should be pulled from the salt `get` functions
    such as config.get

    .. code-block:: python

        __salt__["config.get"]("foo:bar")


    The `get` functions also allow for dict traversal via the *:* delimiter.
    Consider using get functions whenever using ``__opts__`` or ``__pillar__``
    and ``__grains__`` (when using grains for configuration data)

The configuration file data made available in the ``__opts__`` dictionary is the
configuration data relative to the running daemon. If the modules are loaded and
executed by the master, then the master configuration data is available, if the
modules are executed by the minion, then the minion configuration is
available. Any additional information passed into the respective configuration
files is made available

__salt__
--------

Defined in: Auth, Beacons, Engines, Execution, Executors, Outputters, Pillars,
Proxies, Renderers, Returners, Runners, SDB, SSH Wrappers, State, Thorium

``__salt__`` contains the execution module functions. This allows for all
functions to be called as they have been set up by the salt loader.

.. code-block:: python

    __salt__["cmd.run"]("fdisk -l")
    __salt__["network.ip_addrs"]()

.. note::

    When used in runners or outputters, ``__salt__`` references other
    runner/outputter modules, and not execution modules.

__grains__
----------

Filled in for: Execution, Pillar, Renderer, Returner, SSH Wrapper, State.

The ``__grains__`` dictionary contains the grains data generated by the minion
that is currently being worked with. In execution modules, state modules and
returners this is the grains of the minion running the calls, when generating
the external pillar the ``__grains__`` is the grains data from the minion that
the pillar is being generated for.

While ``__grains__`` is defined for every module, it's only filled in for some.

__pillar__
-----------

Filled in for: Execution, Renderer, Returner, SSH Wrapper, State

The ``__pillar__`` dictionary contains the pillar for the respective minion.

While ``__pillar__`` is defined for every module, it's only filled in for some.

__ext_pillar__
--------------

Filled in for: Pillar

The ``__ext_pillar__`` dictionary contains the external pillar modules.

.. _dunder-context:

__context__
-----------

During a state run the ``__context__`` dictionary persists across all states
that are run and then is destroyed when the state ends.

When running an execution module ``__context__`` persists across all module
executions until the modules are refreshed; such as when
:py:func:`saltutil.sync_all <salt.modules.saltutil.sync_all>` or
:py:func:`state.apply <salt.modules.state.apply_>` are executed.

.. code-block:: python

    if not "cp.fileclient" in __context__:
        __context__["cp.fileclient"] = salt.fileclient.get_file_client(__opts__)


.. note:: Because __context__ may or may not have been destroyed, always be
          sure to check for the existence of the key in __context__ and
          generate the key before using it.

__utils__
---------
Defined in: Cloud, Engine, Execution, File Server, Grain, Pillar, Proxy, Roster, Runner, SDB, State

__proxy__
---------
Defined in: Beacon, Engine, Execution, Executor, Proxy, Renderer, Returner, State, Util

__runner__
-----------
Defined in: Engine, Roster, Thorium

.. note:: When used in engines, it should be called __runners__ (plural)

__executors__
-------------

Defined in: Executor

__ret__
-------
Defined in: Proxy

__thorium__
-----------
Defined in: Thorium

__states__
----------
Defined in: Renderers, State

__serializers__
---------------
Defined in: State

__sdb__
-------
Defined in: SDB


__file_client__
---------------

.. versionchanged:: 3006.5

The ``__file_client__`` dunder was added to states and execution modules. This
enables the use of a file client without haveing to instantiate one in
the module.
