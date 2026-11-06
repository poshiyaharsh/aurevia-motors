"""
Gunicorn production server configuration for Aurevia Motors.
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes (2 * CPU cores + 1 is recommended standard)
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
worker_connections = 1000
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 60))
keepalive = 2

# Process naming
proc_name = 'aurevia_motors_wsgi'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" (%(D)s µs)'

# Security & Worker recycling to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50
preload_app = True
