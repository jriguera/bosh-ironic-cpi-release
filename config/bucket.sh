#!/usr/bin/env bash

# Create the bucket for blobs

BUCKET=bosh-ironic-cpi-release

# s3cmd mb "s3://${BUCKET}"
# s3cmd setacl "s3://${BUCKET}"  --acl-public --recursive
