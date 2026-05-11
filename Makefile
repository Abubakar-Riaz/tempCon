# Makefile

.PHONY: \
	api webhooks websockets \
	dev-api dev-webhooks dev-websockets \
	celery-worker celery-beat celery stop-celery-worker stop-celery-beat stop-celery restart-celery logs-celery \
	start stop restart \
	dev-start dev-stop dev-restart \
	stop-api stop-webhooks stop-websockets \
	logs-api logs-webhooks logs-websockets logs \
	status

API_PORT=5000
WEBHOOKS_PORT=5001
WS_PORT=5002

API_APP=backend.wsgi_api:application
WEBHOOKS_APP=backend.wsgi_webhooks:application
WS_APP=backend.asgi_api:application

API_SETTINGS=backend.settings.api
WEBHOOKS_SETTINGS=backend.settings.webhooks

WORKERS=2
TIMEOUT=30

API_PID=api.pid
WEBHOOKS_PID=webhooks.pid
WS_PID=websockets.pid
CELERY_WORKER_PID=celery_worker.pid
CELERY_BEAT_PID=celery_beat.pid

API_ACCESS_LOG=api_access.log
API_ERROR_LOG=api_error.log
API_DEV_LOG=api.log

WEBHOOKS_ACCESS_LOG=webhooks_access.log
WEBHOOKS_ERROR_LOG=webhooks_error.log
WEBHOOKS_DEV_LOG=webhooks.log

WS_LOG=websockets.log
CELERY_WORKER_LOG=celery_worker.log
CELERY_BEAT_LOG=celery_beat.log

api:
	@echo "Starting API server on port $(API_PORT)"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	gunicorn $(API_APP) \
		--bind 127.0.0.1:$(API_PORT) \
		--workers $(WORKERS) \
		--timeout $(TIMEOUT) \
		--access-logfile $(API_ACCESS_LOG) \
		--error-logfile $(API_ERROR_LOG) \
		--capture-output \
		--daemon \
		--pid $(API_PID)

webhooks:
	@echo "Starting Webhooks server on port $(WEBHOOKS_PORT)"
	@DJANGO_SETTINGS_MODULE=$(WEBHOOKS_SETTINGS) \
	gunicorn $(WEBHOOKS_APP) \
		--bind 127.0.0.1:$(WEBHOOKS_PORT) \
		--workers $(WORKERS) \
		--timeout $(TIMEOUT) \
		--access-logfile $(WEBHOOKS_ACCESS_LOG) \
		--error-logfile $(WEBHOOKS_ERROR_LOG) \
		--capture-output \
		--daemon \
		--pid $(WEBHOOKS_PID)

websockets:
	@echo "Starting WebSocket ASGI server on port $(WS_PORT)"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	daphne -b 127.0.0.1 -p $(WS_PORT) $(WS_APP) \
		> $(WS_LOG) 2>&1 & \
	echo $$! > $(WS_PID)

celery-worker:
	@echo "Starting Celery worker"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	celery -A backend worker -l info \
		> $(CELERY_WORKER_LOG) 2>&1 & \
	echo $$! > $(CELERY_WORKER_PID)

celery-beat:
	@echo "Starting Celery beat"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	celery -A backend beat -l info \
		> $(CELERY_BEAT_LOG) 2>&1 & \
	echo $$! > $(CELERY_BEAT_PID)

celery: celery-worker celery-beat
	@echo "Started Celery worker and beat."

start: api webhooks websockets celery
	@echo "Started API, Webhooks, WebSockets, Celery worker, and Celery beat."

restart: stop start

dev-api:
	@echo "Starting API dev server on port $(API_PORT)"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	python -u manage.py runserver 127.0.0.1:$(API_PORT) \
		> $(API_DEV_LOG) 2>&1 & \
	echo $$! > $(API_PID)

dev-webhooks:
	@echo "Starting Webhooks dev server on port $(WEBHOOKS_PORT)"
	@DJANGO_SETTINGS_MODULE=$(WEBHOOKS_SETTINGS) \
	python -u manage.py runserver 127.0.0.1:$(WEBHOOKS_PORT) \
		> $(WEBHOOKS_DEV_LOG) 2>&1 & \
	echo $$! > $(WEBHOOKS_PID)

dev-websockets:
	@echo "Starting WebSocket dev ASGI server on port $(WS_PORT)"
	@DJANGO_SETTINGS_MODULE=$(API_SETTINGS) \
	daphne -b 127.0.0.1 -p $(WS_PORT) $(WS_APP) \
		> $(WS_LOG) 2>&1 & \
	echo $$! > $(WS_PID)

dev-start: dev-api dev-webhooks dev-websockets celery
	@echo "Started dev API, Webhooks, WebSockets, Celery worker, and Celery beat."

dev-restart: dev-stop dev-start

stop-api:
	@if [ -f $(API_PID) ]; then \
		echo "Stopping API server"; \
		kill `cat $(API_PID)` 2>/dev/null || true; \
		rm -f $(API_PID); \
	else \
		echo "API server is not running"; \
	fi

stop-webhooks:
	@if [ -f $(WEBHOOKS_PID) ]; then \
		echo "Stopping Webhooks server"; \
		kill `cat $(WEBHOOKS_PID)` 2>/dev/null || true; \
		rm -f $(WEBHOOKS_PID); \
	else \
		echo "Webhooks server is not running"; \
	fi

stop-websockets:
	@if [ -f $(WS_PID) ]; then \
		echo "Stopping WebSocket server"; \
		kill `cat $(WS_PID)` 2>/dev/null || true; \
		rm -f $(WS_PID); \
	else \
		echo "WebSocket server is not running"; \
	fi

stop-celery-worker:
	@if [ -f $(CELERY_WORKER_PID) ]; then \
		echo "Stopping Celery worker"; \
		kill `cat $(CELERY_WORKER_PID)` 2>/dev/null || true; \
		rm -f $(CELERY_WORKER_PID); \
	else \
		echo "Celery worker is not running"; \
	fi

stop-celery-beat:
	@if [ -f $(CELERY_BEAT_PID) ]; then \
		echo "Stopping Celery beat"; \
		kill `cat $(CELERY_BEAT_PID)` 2>/dev/null || true; \
		rm -f $(CELERY_BEAT_PID); \
	else \
		echo "Celery beat is not running"; \
	fi

stop-celery: stop-celery-worker stop-celery-beat
	@echo "Stopped Celery worker and beat."

restart-celery: stop-celery celery
	@echo "Restarted Celery worker and beat."

stop: stop-api stop-webhooks stop-websockets stop-celery
	@echo "Stopped API, Webhooks, WebSockets, Celery worker, and Celery beat."

dev-stop: stop

logs-api:
	@touch $(API_DEV_LOG) $(API_ERROR_LOG) $(API_ACCESS_LOG)
	tail -f $(API_DEV_LOG) $(API_ERROR_LOG) $(API_ACCESS_LOG)

logs-webhooks:
	@touch $(WEBHOOKS_DEV_LOG) $(WEBHOOKS_ERROR_LOG) $(WEBHOOKS_ACCESS_LOG)
	tail -f $(WEBHOOKS_DEV_LOG) $(WEBHOOKS_ERROR_LOG) $(WEBHOOKS_ACCESS_LOG)

logs-websockets:
	@touch $(WS_LOG)
	tail -f $(WS_LOG)

logs-celery:
	@touch $(CELERY_WORKER_LOG) $(CELERY_BEAT_LOG)
	tail -f $(CELERY_WORKER_LOG) $(CELERY_BEAT_LOG)

logs:
	@touch $(API_DEV_LOG) $(API_ERROR_LOG) $(API_ACCESS_LOG) \
		$(WEBHOOKS_DEV_LOG) $(WEBHOOKS_ERROR_LOG) $(WEBHOOKS_ACCESS_LOG) \
		$(WS_LOG) \
		$(CELERY_WORKER_LOG) $(CELERY_BEAT_LOG)
	tail -f \
		$(API_DEV_LOG) $(API_ERROR_LOG) $(API_ACCESS_LOG) \
		$(WEBHOOKS_DEV_LOG) $(WEBHOOKS_ERROR_LOG) $(WEBHOOKS_ACCESS_LOG) \
		$(WS_LOG) \
		$(CELERY_WORKER_LOG) $(CELERY_BEAT_LOG)

status:
	@echo "API:"
	@if [ -f $(API_PID) ]; then ps -p `cat $(API_PID)` || true; else echo "  not running"; fi
	@echo "Webhooks:"
	@if [ -f $(WEBHOOKS_PID) ]; then ps -p `cat $(WEBHOOKS_PID)` || true; else echo "  not running"; fi
	@echo "WebSockets:"
	@if [ -f $(WS_PID) ]; then ps -p `cat $(WS_PID)` || true; else echo "  not running"; fi
	@echo "Celery worker:"
	@if [ -f $(CELERY_WORKER_PID) ]; then ps -p `cat $(CELERY_WORKER_PID)` || true; else echo "  not running"; fi
	@echo "Celery beat:"
	@if [ -f $(CELERY_BEAT_PID) ]; then ps -p `cat $(CELERY_BEAT_PID)` || true; else echo "  not running"; fi