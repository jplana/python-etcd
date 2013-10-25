#!/bin/sh
git clone https://github.com/coreos/etcd.git
cd etcd
git checkout v0.1.2
./build


${TRAVIS:?"This is not a Travis build. All Done"}
#Temporal solution to travis issue #155
sudo rm -rf /dev/shm && sudo ln -s /run/shm /dev/shm
echo "All Done"
