#!/bin/bash
set -e
VERSION=${1:-2.3.7}
mkdir -p bin
URL="https://github.com/coreos/etcd/releases/download/v${VERSION}/etcd-v${VERSION}-linux-amd64.tar.gz"
curl -L $URL | tar -C ./bin --strip-components=1 -xzvf - "etcd-v${VERSION}-linux-amd64/etcd"
mv bin/etcd /usr/local/bin/
