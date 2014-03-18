Python-etcd documentation
=========================

A python client for Etcd https://github.com/coreos/etcd




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

   import etcd

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

    client.write('/nodes/n1', 1)
    # with ttl
    client.write('/nodes/n2', 2, ttl=4)  # sets the ttl to 4 seconds
    # create only
    client.write('/nodes/n3', 'test', prevExist=False)
    # Compare and swap values atomically
    client.write('/nodes/n3', 'test2', prevValue='test1') #this fails to write
    client.write('/nodes/n3', 'test2', prevIndex=10) #this fails to write
    # mkdir
    client.write('/nodes/queue', dir=True)
    # Append a value to a queue dir
    client.write('/nodes/queue', 'test', append=True) #will write i.e. /nodes/queue/11
    client.write('/nodes/queue', 'test2', append=True) #will write i.e. /nodes/queue/12

You can also atomically update a result:

.. code:: python

    result = client.read('/foo')
    print(result.value) # bar
    result.value += u'bar'
    updated = client.update(result) # if any other client wrote '/foo' in the meantime this will fail
    print(updated.value) # barbar



Get a key
.........

.. code-block:: python

    client.read('/nodes/n2').value
    #recursively read a directory
    r = client.read('/nodes', recursive=True, sorted=True)
    for child in r.children:
        print("%s: %s" % (child.key,child.value))

    client.read('/nodes/n2', wait=True) #Waits for a change in value in the key before returning.
    client.read('/nodes/n2', wait=True, waitIndex=10)



Delete a key
............

.. code-block:: python

    client.delete('/nodes/n1')
    client.delete('/nodes', dir=True) #spits an error if dir is not empty
    client.delete('/nodes', recursive=True) #this works recursively




Use lock primitives
...................

.. code-block:: python

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

Use the leader election primitives
..................................

.. code-block:: python

    # Set a leader object with a name; if no name is given, the local hostname
    # is used.
    # Zero or no ttl means the leader object is persistent.
    client = etcd.Client()
    client.election.set('/mysql', name='foo.example.com', ttl=120) # returns the etcd index

    # Get the name
    print(client.election.get('/mysql')) # 'foo.example.com'
    # Delete it!
    print(client.election.delete('/mysql', name='foo.example.com'))



Get machines in the cluster
...........................

.. code-block:: python

    client.machines


Get leader of the cluster
.........................

.. code-block:: python

    client.leader




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
