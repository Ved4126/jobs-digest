#!/bin/bash
set -e

cd /Users/veddabhi/Documents/jobs_digest

/Users/veddabhi/Documents/jobs_digest/venv/bin/python \
  /Users/veddabhi/Documents/jobs_digest/google_jobs_digest.py \
  >> /Users/veddabhi/Documents/jobs_digest/job_digest.log 2>&1