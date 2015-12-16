from setuptools import setup, find_packages
import sys, os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.4.3'

# Dnspython is two different packages depending on python version
if sys.version_info[0] == 2:
    dns = 'dnspython'
else:
    dns = 'dnspython3'

install_requires = [
    'urllib3>=1.7.1',
    dns
]

test_requires = [
    'mock',
    'nose',
    'pyOpenSSL>=0.14'
]

setup(
    name='python-etcd',
    version=version,
    description="A python client for etcd",
    long_description=README + '\n\n' + NEWS,
    classifiers=[
        "Topic :: System :: Distributed Computing",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Database :: Front-Ends",
    ],
    keywords='etcd raft distributed log api client',
    author='Jose Plana',
    author_email='jplana@gmail.com',
    url='http://github.com/jplana/python-etcd',
    license='MIT',
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='nose.collector',
)
