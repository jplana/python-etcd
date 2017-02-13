#!/bin/sh

if [  $# -gt 0 ]
    then
    ETCD_VERSION="$1";
    else
    ETCD_VERSION="master";
fi

echo "Using ETCD version $ETCD_VERSION"

BASE=$PWD
mkdir -p gopath/src/coreos/
export GOPATH=$BASE/gopath/
cd $GOPATH/src/coreos
git clone https://github.com/coreos/etcd.git
cd etcd
git checkout -b buildout $ETCD_VERSION
./build
cd $BASE
cp -r $GOPATH/src/coreos/etcd/bin .


${TRAVIS:?"This is not a Travis build. All Done"}
#Temporal solution to travis issue #155
sudo rm -rf /dev/shm && sudo ln -s /run/shm /dev/shm
echo "All Done"
