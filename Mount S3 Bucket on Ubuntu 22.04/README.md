# Mount S3 Bucket on Ubuntu 22.04

## Introduction
In this tutorial, I will instruct you on how to mount an AWS S3 Bucket on the Ubuntu file system. S3FS is a tool that lets you treat your Amazon S3 cloud storage like a regular folder on your computer. It makes it easy to copy files to and from the cloud, essentially allowing you to use your S3 storage just like you would use a USB drive or an external hard disk.

## Requirements 
- Ubuntu 18.04 or highier
- At least 10GB of storage
- Active AWS account
- S3 Bucket configured with the appropriate permissions

  *(See [Mount S3 Bucket on Windows File Explorer](https://github.com/ThePinkPanther96/AWS/blob/main/Mount%20S3%20Bucket%20on%20Windows%20File%20Explorer/README.md) to learn how to create S3 and IAM permissions)*

## Configuration 
1. Update the system and install [s3fs-fuse](https://github.com/s3fs-fuse/s3fs-fuse)
  ```
  sudo apt update -y
  sudo apt install s3fs -y
  ```
2. 