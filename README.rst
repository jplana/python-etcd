python-etcd documentation
=========================

A python client for Etcd https://github.com/coreos/etcd

Official documentation: http://python-etcd.readthedocs.org/

.. image:: https://travis-ci.org/jplana/python-etcd.png?branch=master
   :target: https://travis-ci.org/jplana/python-etcd

.. image:: https://coveralls.io/repos/jplana/python-etcd/badge.svg?branch=master&service=github
   :target: https://coveralls.io/github/jplana/python-etcd?branch=master

Installation
------------

Pre-requirements
~~~~~~~~~~~~~~~~

Install etcd (2.0.1 or later). This version of python-etcd will only work correctly with the etcd version 2.0.x or later. If you are running an older version of etcd, please use python-etcd 0.3.3 or earlier.

This client is known to work with python 2.7 and with python 3.3 or above. It is not tested or expected to work in more outdated versions of python.

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
    # If you have defined a SRV record for _etcd._tcp.example.com pointing to the clients
    client = etcd.Client(srv_domain='example.com', protocol="https")
    # create a client against https://api.example.com:443/etcd
    client = etcd.Client(host='api.example.com', protocol='https', port=443, version_prefix='/etcd')
Write a key
~~~~~~~~~

.. code:: python

    client.write('/nodes/n1', 1)
    # with ttl
    client.write('/nodes/n2', 2, ttl=4)  # sets the ttl to 4 seconds
    client.set('/nodes/n2', 1) # Equivalent, for compatibility reasons.

Read a key
~~~~~~~~~

.. code:: python

    client.read('/nodes/n2').value
    client.read('/nodes', recursive = True) #get all the values of a directory, recursively.
    client.get('/nodes/n2').value

    # raises etcd.EtcdKeyNotFound when key not found
    try:
        client.read('/invalid/path')
    except etcd.EtcdKeyNotFound:
        # do something
        print "error"


Delete a key
~~~~~~~~~~~~

.. code:: python

    client.delete('/nodes/n1')

Atomic Compare and Swap
~~~~~~~~~~~~

.. code:: python

    client.write('/nodes/n2', 2, prevValue = 4) # will set /nodes/n2 's value to 2 only if its previous value was 4 and
    client.write('/nodes/n2', 2, prevExist = False) # will set /nodes/n2 's value to 2 only if the key did not exist before
    client.write('/nodes/n2', 2, prevIndex = 30) # will set /nodes/n2 's value to 2 only if the key was last modified at index 30
    client.test_and_set('/nodes/n2', 2, 4) #equivalent to client.write('/nodes/n2', 2, prevValue = 4)

You can also atomically update a result:

.. code:: python

    result = client.read('/foo')
    print(result.value) # bar
    result.value += u'bar'
    updated = client.update(result) # if any other client wrote '/foo' in the meantime this will fail
    print(updated.value) # barbar

Watch a key
~~~~~~~~~~~

.. code:: python

    client.read('/nodes/n1', wait = True) # will wait till the key is changed, and return once its changed
    client.read('/nodes/n1', wait = True, timeout=30) # will wait till the key is changed, and return once its changed, or exit with an exception after 30 seconds.
    client.read('/nodes/n1', wait = True, waitIndex = 10) # get all changes on this key starting from index 10
    client.watch('/nodes/n1') #equivalent to client.read('/nodes/n1', wait = True)
    client.watch('/nodes/n1', index = 10)

Locking module
~~~~~~~~~~~~~~

.. code:: python

    # Initialize the lock object:
    # NOTE: this does not acquire a lock yet
    client = etcd.Client()
    lock = etcd.Lock(client, 'my_lock_name')

    # Use the lock object:
    lock.acquire(blocking=True, # will block until the lock is acquired
          lock_ttl=None) # lock will live until we release it
    lock.is_acquired()  #
    lock.acquire(lock_ttl=60) # renew a lock
    lock.release() # release an existing lock
    lock.is_acquired()  # False

    # The lock object may also be used as a context manager:
    client = etcd.Client()
    with etcd.Lock(client, 'customer1') as my_lock:
        do_stuff()
        my_lock.is_acquired()  # True
        my_lock.acquire(lock_ttl = 60)
    my_lock.is_acquired() # False


Get machines in the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    client.machines

Get leader of the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    client.leader

Generate a sequential key in a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    x = client.write("/dir/name", "value", append=True)
    print("generated key: " + x.key)
    print("stored value: " + x.value)

List contents of a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    #stick a couple values in the directory
    client.write("/dir/name", "value1", append=True)
    client.write("/dir/name", "value2", append=True)

    directory = client.get("/dir/name")

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
