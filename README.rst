python-etcd documentation
=========================

A python client for Etcd https://github.com/coreos/etcd

Official documentation: http://python-etcd.readthedocs.org/

.. image:: https://travis-ci.org/jplana/python-etcd.png?branch=master
   :target: https://travis-ci.org/jplana/python-etcd

Installation
------------

Pre-requirements
~~~~~~~~~~~~~~~~

Install etcd (0.2.rc1 or later). This version of python-etcd will only work correctly with the etcd API version 2.

This client is known to work with python 2.7 and with python 3.3 or above. It is not tested or expected to work in more outddated versions of python.

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

Delete a key
~~~~~~~~~~~~

.. code:: python

    client.delete('/nodes/n1')

Atomic Compare and Swap
~~~~~~~~~~~~

.. code:: python

    client.write('/nodes/n2', 2, prevValue = 4) # will set /nodes/n2 's value to 2 only if its previous value was 4 and
    client.write('/nodes/n2', 2, prevExists = False) # will set /nodes/n2 's value to 2 only if the key did not exist before
    client.write('/nodes/n2', 2, prevIndex = 30) # will set /nodes/n2 's value to 2 only if the key was last modified at index 30
    client.test_and_set('/nodes/n2', 2, 4) #equivalent to client.write('/nodes/n2', 2, prevValue = 4)


Watch a key
~~~~~~~~~~~

.. code:: python

    client.read('/nodes/n1', watch = True) # will wait till the key is changed, and return once its changed
    client.read('/nodes/n1', watch = True, watchIndex = 10) # get all changes on this key starting from index 10
    client.watch('/nodes/n1') #equivalent to client.read('/nodes/n1', watch = True)
    client.watch('/nodes/n1', index = 10)

Get a lock
~~~~~~~~~~

.. code:: python

    # Initialize the lock object:
    # NOTE: this does not acquire a lock yet
    client = etcd.Client()
    lock = client.get_lock('/customer1', ttl=60)

    # Use the lock object:
    lock.acquire()
    lock.is_locked()  # True
    lock.renew(60)
    lock.release()
    lock.is_locked()  # False

    # The lock object may also be used as a context manager:
    client = etcd.Client()
    lock = client.get_lock('/customer1', ttl=60)
    with lock as my_lock:
        do_stuff()
        lock.is_locked()  # True
        lock.renew(60)
    lock.is_locked()  # False

Get machines in the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    client.machines

Get leader of the cluster
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    client.leader

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
