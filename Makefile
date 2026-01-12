
LOG_DIR=./logs
LOG_PID_FILE=./logs/.capture.pid

.PHONY: logs logs-start logs-stop logs-today logs-errors logs-service logs-search logs-rotate logs-status logs-clean logs-cron-install logs-cron-remove logdirs

logs:
	docker compose logs -f --tail 300

# Log Management - Capture and filter logs
logdirs:
	@mkdir -p $(LOG_DIR)

logs-start: logdirs
	@if [ -f $(LOG_PID_FILE) ] && kill -0 $$(cat $(LOG_PID_FILE)) 2>/dev/null; then \
		echo "Log capture already running (PID: $$(cat $(LOG_PID_FILE)))"; \
	else \
		echo "Starting background log capture to $(LOG_DIR)/$$(date +%Y-%m-%d).log"; \
		nohup docker compose logs -f >> $(LOG_DIR)/$$(date +%Y-%m-%d).log 2>&1 & \
		echo $$! > $(LOG_PID_FILE); \
		echo "Log capture started (PID: $$!)"; \
	fi

logs-stop:
	@if [ -f $(LOG_PID_FILE) ] && kill -0 $$(cat $(LOG_PID_FILE)) 2>/dev/null; then \
		kill $$(cat $(LOG_PID_FILE)) && rm -f $(LOG_PID_FILE) && echo "Log capture stopped"; \
	else \
		rm -f $(LOG_PID_FILE); \
		echo "No log capture process running"; \
	fi

logs-today:
	@cat $(LOG_DIR)/$$(date +%Y-%m-%d).log 2>/dev/null || echo "No logs captured today. Run 'make logs-start' first."

logs-errors:
	@grep -i "error\|exception\|fail" $(LOG_DIR)/*.log 2>/dev/null || echo "No errors found in captured logs"

logs-service:
	@grep "^$(SERVICE)" $(LOG_DIR)/$$(date +%Y-%m-%d).log 2>/dev/null || echo "No logs for $(SERVICE). Try: make logs-service SERVICE=outpost"

logs-search:
	@grep -i "$(PATTERN)" $(LOG_DIR)/*.log 2>/dev/null || echo "Pattern '$(PATTERN)' not found"

logs-rotate:
	@find $(LOG_DIR) -name "*.log" -mtime +3 -exec gzip {} \; 2>/dev/null || true
	@find $(LOG_DIR) -name "*.log.gz" -mtime +7 -delete 2>/dev/null || true
	@echo "Log rotation complete (compressed >3 days, deleted >7 days)"

logs-status:
	@echo "Log directory: $(LOG_DIR)"
	@du -sh $(LOG_DIR) 2>/dev/null || echo "No logs yet"
	@echo ""
	@ls -lh $(LOG_DIR)/ 2>/dev/null || echo "No log files"

logs-clean:
	@read -p "Delete all captured logs? [y/N] " confirm && \
	[ "$$confirm" = "y" ] && rm -rf $(LOG_DIR)/* && echo "Logs deleted" || echo "Cancelled"

logs-cron-install:
	@DKPROXY_DIR=$$(pwd) && \
	(crontab -l 2>/dev/null | grep -v "dkproxy.*logs-rotate"; \
	echo "0 0 * * * cd $$DKPROXY_DIR && make logs-rotate >> $$DKPROXY_DIR/logs/cron.log 2>&1") | crontab - && \
	echo "Cron job installed: daily log rotation at midnight" && \
	echo "View with: crontab -l"

logs-cron-remove:
	@crontab -l 2>/dev/null | grep -v "dkproxy.*logs-rotate" | crontab - && \
	echo "Cron job removed"

prepare:
	echo "Adding the repository to Apt sources..."

p2:
	echo \
		"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
		$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
		sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

build: down ensureitems
	docker compose build --no-cache

down:
	docker compose down --remove-orphans

update: down pull build
	echo "Proxy updated.  Bring it up with make up logs"

up: down ensureitems logdirs
	docker compose up -d
	@echo "Starting background log capture..."
	@nohup docker compose logs -f >> $(LOG_DIR)/$$(date +%Y-%m-%d).log 2>&1 & echo $$! > $(LOG_PID_FILE)

download:
	sudo rm -Rf main.zip proxy.tar.bz2 dkproxy-main
	sudo wget https://github.com/dagknows/dkproxy/archive/refs/heads/main.zip
	sudo unzip main.zip
	sudo tar --strip-components=1 -zcvf proxy.tar.bz2 dkproxy-main
	sudo tar -zxvf proxy.tar.bz2
	sudo rm -Rf main.zip proxy.tar.bz2 dkproxy-main
	sudo chown -R ${USER} .

ensureitems:
	touch outpost/requirements.txt
	touch cmd_exec/requirements.txt
	-mkdir -p ./outpost/sidecar/pyrunner
	-mkdir -p ./outpost/sidecar/statuses
	-sudo chmod -R a+rw ./outpost/sidecar
	-sudo chmod a+rx ./outpost/sidecar ./outpost/sidecar/statuses ./outpost/sidecar/pyrunner
	-sudo chmod -R a+rwx cmd_exec/logs
	-sudo chmod -R a+rwx outpost/logs
	-sudo chmod -R a+rwx outpost/jobs
	-sudo chmod -R a+rwx vault/data

pull:
	docker pull public.ecr.aws/n5k3t9x2/outpost:latest
	docker pull public.ecr.aws/n5k3t9x2/cmd_exec:latest

help:
	@echo "DagKnows Proxy Management Commands"
	@echo "==================================="
	@echo ""
	@echo "Service Management:"
	@echo "  make up           - Start proxy services (+ auto log capture)"
	@echo "  make down         - Stop all services"
	@echo "  make build        - Build Docker images"
	@echo "  make update       - Update to latest version"
	@echo "  make pull         - Pull latest Docker images"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs         - View live logs (last 300 lines + follow)"
	@echo ""
	@echo "Log Management:"
	@echo "  make logs-start        - Start background log capture"
	@echo "  make logs-stop         - Stop background log capture"
	@echo "  make logs-today        - View today's captured logs"
	@echo "  make logs-errors       - View errors from captured logs"
	@echo "  make logs-service SERVICE=outpost - View specific service"
	@echo "  make logs-search PATTERN='text' - Search logs for pattern"
	@echo "  make logs-rotate       - Compress old, delete >7 days"
	@echo "  make logs-status       - Show log disk usage"
	@echo "  make logs-clean        - Delete all captured logs"
	@echo "  make logs-cron-install - Setup daily auto-rotation (cron)"
	@echo "  make logs-cron-remove  - Remove auto-rotation cron job"
