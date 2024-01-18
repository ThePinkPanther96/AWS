#!/bin/bash

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <bucket_name> <access_key> <secret_key>"
    exit 1
fi

bucket_name="$1"
access_key="$2"
secret_key="$3"

sudo apt update -y
sudo apt install s3fs -y

sudo mkdir /mnt/$bucket_name

echo $access_key:$secret_key > ~/.passwd-s3fs
chmod 600 ${HOME}/.passwd-s3fs

echo "user_allow_other" | sudo tee -a /etc/fuse.conf

echo "s3fs#$bucket_name:/ /mnt/$bucket_name fuse allow_other 0 0" | sudo tee -a /etc/fstab


