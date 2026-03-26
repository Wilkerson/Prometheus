"""Gunicorn config para producao."""
import multiprocessing

# Bind
bind = "0.0.0.0:8000"

# Workers: 2-4 x CPU cores
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Restart workers periodicamente (evita memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Preload app (compartilha memoria entre workers)
preload_app = True

# Nome do processo
proc_name = "prometheus"
