python-etcd documentation
=========================

A python client for Etcd https://github.com/coreos/etcd

Official documentation: http://python-aio-etcd.readthedocs.org/

.. image:: https://travis-ci.org/jplana/python-etcd.png?branch=master
   :target: https://travis-ci.org/jplana/python-etcd

Installation
------------

Pre-requirements
~~~~~~~~~~~~~~~~

Install etcd (2.0.1 or later). This version of python-aioetcd will only work correctly with the version 2.0.x or later.

This client is known to work with python 3.4 or above. It is not tested or expected to work in more outdated versions of python.

Python 2 is not supported.

From source
~~~~~~~~~~~

.. code:: bash

    $ python setup.py install

Usage
-----

The basic methods of the client have changed compared to previous versions, to reflect the new API structure; however a compatibility layer has been maintained so that you don't necessarily need to rewrite all your existing code.

Create a client object
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    import etcd

    client = etcd.Client() # this will create a client against etcd server running on localhost on port 4001
    client = etcd.Client(port=4002)
    client = etcd.Client(host='127.0.0.1', port=4003)
    client = etcd.Client(host='127.0.0.1', port=4003, allow_redirect=False) # wont let you run sensitive commands on non-leader machines, default is true
    # create a client against https://api.example.com:443/etcd
    client = etcd.Client(host='api.example.com', protocol='https', port=443, version_prefix='/etcd')
Write a key
~~~~~~~~~

.. code:: python

    yield from client.write('/nodes/n1', 1)
    # with ttl
    yield from client.write('/nodes/n2', 2, ttl=4)  # sets the ttl to 4 seconds
    yield from client.set('/nodes/n2', 1) # Equivalent, for compatibility reasons.

Read a key
~~~~~~~~~

.. code:: python

    yield from client.read('/nodes/n2').value
    yield from client.read('/nodes', recursive = True) #get all the values of a directory, recursively.
    yield from client.get('/nodes/n2').value

Delete a key
~~~~~~~~~~~~

.. code:: python

    yield from client.delete('/nodes/n1')

Atomic Compare and Swap
~~~~~~~~~~~~

.. code:: python

    yield from client.write('/nodes/n2', 2, prevValue = 4) # will set /nodes/n2 's value to 2 only if its previous value was 4 and
    yield from client.write('/nodes/n2', 2, prevExist = False) # will set /nodes/n2 's value to 2 only if the key did not exist before
    yield from client.write('/nodes/n2', 2, prevIndex = 30) # will set /nodes/n2 's value to 2 only if the key was last modified at index 30
    yield from client.test_and_set('/nodes/n2', 2, 4) #equivalent to client.write('/nodes/n2', 2, prevValue = 4)

You can also atomically update a result:

.. code:: python

    result = yield from client.read('/foo')
    print(result.value) # bar
    result.value += u'bar'
    updated = yield from client.update(result) # if any other client wrote '/foo' in the meantime this will fail
    print(updated.value) # barbar

Watch a key
~~~~~~~~~~~

.. code:: python

    result = yield from client.read('/nodes/n1', wait = True) # will wait till the key is changed, and return once its changed
    result = yield from client.read('/nodes/n1', wait = True, waitIndex = 10) # get all changes on this key starting from index 10
    result = yield from client.watch('/nodes/n1') #equivalent to client.read('/nodes/n1', wait = True)
    result = yield from client.watch('/nodes/n1', index = 10)

If you want to time out the read() call, wrap it in `asyncio.wait_for`:

.. code:: python

    result = yield from asyncio.wait_for(client.read('/nodes/n1', wait = True), timeout=30)

Locking module
~~~~~~~~~~~~~~

.. code:: python

    # Initialize the lock object:
    # NOTE: this does not acquire a lock yet
    from aioetcd.lock import Lock

    client = etcd.Client()
    lock = Lock(client, 'my_lock_name')

    # Use the lock object:
    yield from lock.acquire(blocking=True, # will block until the lock is acquired
          lock_ttl=None) # lock will live until we release it
    yield from lock.is_acquired()  #
    yield from lock.acquire(lock_ttl=60) # renew a lock
    yield from lock.release() # release an existing lock
    yield from lock.is_acquired()  # False

    # The lock object may also be used as a context manager (Python 3.5):
    async with Lock('customer1') as my_lock:
        do_stuff()
        await my_lock.is_acquired()  # True
        await my_lock.acquire(lock_ttl = 60)
    await my_lock.is_acquired() # False


Get machines in the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    machiens = yield from client.machines()

Get leader of the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    leaderinfo = yield from client.leader()

Generate a sequential key in a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    x = yield from client.write("/dir/name", "value", append=True)
    print("generated key: " + x.key)
    print("stored value: " + x.value)

List contents of a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    #stick a couple values in the directory
    yield from client.write("/dir/name", "value1", append=True)
    yield from client.write("/dir/name", "value2", append=True)

    directory = yield from client.get("/dir/name")

    # loop through directory children
    for result in directory.children:
      print(result.key + ": " + result.value)

    # or just get the first child value
    print(directory.children.next().value)

Development setup
-----------------

To create a buildout,

.. code:: bash

    $ python bootstrap.py
    $ bin/buildout

to test you should have etcd available in your system path:

.. code:: bash

    $ bin/test

to generate documentation,

.. code:: bash

    $ cd docs
    $ make

Release HOWTO
-------------

To make a release

    1) Update release date/version in NEWS.txt and setup.py
    2) Run 'python setup.py sdist'
    3) Test the generated source distribution in dist/
    4) Upload to PyPI: 'python setup.py sdist register upload'
