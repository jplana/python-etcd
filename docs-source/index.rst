Python-etcd documentation
=========================

An asynchronous python client for Etcd https://github.com/coreos/etcd




Installation
------------

Pre-requirements
................

Install etcd


From source
...........

.. code-block:: bash

    $ python setup.py install


Usage
-----

Create a client object
......................

.. code-block:: python

   import aioetcd as etcd

   client = etcd.Client() # this will create a client against etcd server running on localhost on port 4001
   client = etcd.Client(port=4002)
   client = etcd.Client(host='127.0.0.1', port=4003)
   client = etcd.Client(host='127.0.0.1', port=4003, allow_redirect=False) # wont let you run sensitive commands on non-leader machines, default is true
   client = etcd.Client(
                host='127.0.0.1',
                port=4003,
                allow_reconnect=True,
                protocol='https',)

Set a key
.........

.. code-block:: python

    yield from client.write('/nodes/n1', 1)
    # with ttl
    yield from client.write('/nodes/n2', 2, ttl=4)  # sets the ttl to 4 seconds
    # create only
    yield from client.write('/nodes/n3', 'test', prevExist=False)
    # Compare and swap values atomically
    yield from client.write('/nodes/n3', 'test2', prevValue='test1') #this fails to write
    yield from client.write('/nodes/n3', 'test2', prevIndex=10) #this fails to write
    # mkdir
    yield from client.write('/nodes/queue', dir=True)
    # Append a value to a queue dir
    yield from client.write('/nodes/queue', 'test', append=True) #will write i.e. /nodes/queue/11
    yield from client.write('/nodes/queue', 'test2', append=True) #will write i.e. /nodes/queue/12

You can also atomically update a result:

.. code:: python

    result = yield from client.read('/foo')
    print(result.value) # bar
    result.value += u'bar'
    updated = yield from client.update(result) # if any other client wrote '/foo' in the meantime this will fail
    print(updated.value) # barbar



Get a key
.........

.. code-block:: python

    (yield from client.read('/nodes/n2')).value
    #recursively read a directory
    r = yield from client.read('/nodes', recursive=True, sorted=True)
    for child in r.children:
        print("%s: %s" % (child.key,child.value))

    yield from client.read('/nodes/n2', wait=True) #Waits for a change in value in the key before returning.
    yield from client.read('/nodes/n2', wait=True, waitIndex=10)



Delete a key
............

.. code-block:: python

    yield from client.delete('/nodes/n1')
    yield from client.delete('/nodes', dir=True) #spits an error if dir is not empty
    yield from client.delete('/nodes', recursive=True) #this works recursively




Use lock primitives
...................

.. code-block:: python

    # Initialize the lock object:
    # NOTE: this does not acquire a lock yet
    from aioetcd.lock import Lock
    client = etcd.Client()
    lock = Lock(client, '/customer1')

    # Use the lock object:
    yield from lock.acquire(lock_ttl=60)
    state = yield from lock.is_locked()  # True
    yield from lock.renew(60)
    yield from lock.release()
    state = yield from lock.is_locked()  # False

    # The lock object may also be used as a context manager:
    # (Python 3.5+)
    client = etcd.Client()
    lock = Lock(client, '/customer1')
    async with lock as my_lock:
        do_stuff()
        state = await lock.is_locked()  # True
        await lock.renew(60)
    state = yield from lock.is_locked()  # False


Get machines in the cluster
...........................

.. code-block:: python

    machines = yield from client.machines()


Get leader of the cluster
.........................

.. code-block:: python

    leader_info = yield from client.leader()


Development setup
-----------------

To create a buildout,

.. code-block:: bash

  $ python bootstrap.py
  $ bin/buildout


to test you should have etcd available in your system path:

.. code-block:: bash

  $ bin/test

to generate documentation,

.. code-block:: bash

  $ cd docs
  $ make



Release HOWTO
-------------

To make a release,

  1) Update release date/version in NEWS.txt and setup.py
  2) Run 'python setup.py sdist'
  3) Test the generated source distribution in dist/
  4) Upload to PyPI: 'python setup.py sdist register upload'
  5) Increase version in setup.py (for next release)


List of contributors at https://github.com/jplana/python-etcd/graphs/contributors

Code documentation
------------------

.. toctree::
   :maxdepth: 2

   api.rst
