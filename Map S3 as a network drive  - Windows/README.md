# Map S3 Bucket to a network shared drive on Windows
## Introduction
In this tutorial, I will instruct you how to convert a regular S3 Bucket on AWS to a functioning shared network drive on your Windows endpoint with a few open-source tools and a relatively simple PowerShell script. this is an inexpensive and easy solution to store and share mass data from multiple endpoints without the need to constantly keep track of the disk and expand storage space. since it is based on S3 Bucket it is also elastic storage, that expands by demand and doesn't need to be 
I first encountered this great open-source solution when I was tasked in my job to think of and execute a solution for storing a great number of system logs by our QA team. So, let's get started!


## Requirements
- An active AWS account with administrative privileges.
- Windows 10/11 based endpint.
- Basic understanding in PowerShell.
- Basic understanding in JSON.

