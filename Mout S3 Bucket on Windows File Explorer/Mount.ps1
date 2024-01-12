# In place of "BUCKET_NAME" put the name of your S3 Bucket.
cmd /c "c:\rclone\rclone\rclone.exe"  mount BUCKET_NAME:/BUCKET_NAME/ Q: --vfs-cache-mode full 
