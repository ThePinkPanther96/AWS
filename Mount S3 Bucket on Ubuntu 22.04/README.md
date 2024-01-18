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
3. Create a mounting point
   
   ```
   mkdir /mnt/BUCKET NAME>
   ```
4. Create a configuration file with the IAM Access key & Secret key
   
   ```
   echo ACCESS_KEY:SECRET_ACCESS_KEY > ~/.passwd-s3fs
   ```
   *See example: ```echo AKIA4SK3HPQ9FLWO8AMB:esrhLH4m1Da+3fJoU5xet1/ivsZ+Pay73BcSnzP > ~/.passwd-s3fs```*
5. Set the correct permissions

   ```
   chmod 600 ${HOME}/.passwd-s3fs
   ```
   *NOTE! ${HOME} must stay as such*
6. Add *user_allow_other* to *```/etc/fuse.conf```* to allow all users to access the S3

   ```
   echo "user_allow_other" | sudo tee -a /etc/fuse.conf
   ```
7. Finally, add it ```fstab``` so the S3 will be mounted at startup

   ```
   echo "s3fs#<BUCKET NAME>:/ /mnt/<BUCKET NAME> fuse allow_other 0 0" | sudo tee -a /etc/fstab
   ```

## Additional commands
- Mount the Bucket
  
  ```
  s3fs <BUCKET NAME>:/ /mnt/<BUCKET NAME>/ -o allow_other
  ```
- Unmount the Bucket
  
  ```
  sudo umount /mnt/<BUCKET NAME>
  ```
- 
  

   
