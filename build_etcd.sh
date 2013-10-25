#!/bin/sh
git clone https://github.com/coreos/etcd.git
cd etcd
git checkout v0.1.2
./build

#Temporal solution to travis issue #155
sudo rm -rf /dev/shm && sudo ln -s /run/shm /dev/shm
