from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.4.2'

install_requires = [
    'aiohttp',
]

test_requires = [
    'pytest',
]

setup(
    name='aioetcd',
    version=version,
    description="An asynchronous python client for etcd",
    long_description=README,
    classifiers=[
        "Topic :: System :: Distributed Computing",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Database :: Front-Ends",
    ],
    keywords='etcd raft distributed log api client',
    author='Mathias Urlichs',
    author_email='matthias@urlichs.de',
    url='http://github.com/smurfix/aioetcd',
    license='MIT',
    packages=find_packages('aioetcd'),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='pytest.collector',
)
