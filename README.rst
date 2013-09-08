python-etcd documentation
=========================

A python client for Etcd https://github.com/coreos/etcd

Installation
------------

Pre-requirements
~~~~~~~~~~~~~~~~

Install etcd

From source
~~~~~~~~~~~

.. code:: bash

    $ python setup.py install

Usage
-----

Create a client object
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    import etcd

    client = etcd.Client() # this will create a client against etcd server running on localhost on port 4001
    client = etcd.Client(port=4002)
    client = etcd.Client(host='127.0.0.1', port=4003)
    client = etcd.Client(host='127.0.0.1', port=4003, allow_redirect=False) # wont let you run sensitive commands on non-leader machines, default is true

Set a key
~~~~~~~~~

.. code:: python

    client.set('/nodes/n1', 1)
    # with ttl
    client.set('/nodes/n2', 2, ttl=4)  # sets the ttl to 4 seconds

Get a key
~~~~~~~~~

.. code:: python

    client.get('/nodes/n2')['value']

Delete a key
~~~~~~~~~~~~

.. code:: python

    client.delete('/nodes/n1')

Test and set
~~~~~~~~~~~~

.. code:: python

    client.test_and_set('/nodes/n2', 2, 4) # will set /nodes/n2 's value to 2 only if its previous value was 4

Watch a key
~~~~~~~~~~~

.. code:: python

    client.watch('/nodes/n1') # will wait till the key is changed, and return once its changed

List sub keys
~~~~~~~~~~~~~

.. code:: python

    client.get('/nodes')

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
