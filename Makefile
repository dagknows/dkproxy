
LOG_DIR=./logs
LOG_PID_FILE=./logs/.capture.pid

.PHONY: logs logs-start logs-stop logs-today logs-errors logs-service logs-search logs-rotate logs-status logs-clean logs-cron-install logs-cron-remove logdirs

logs:
	docker compose logs -f --tail 300

# Log Management - Capture and filter logs
logdirs:
	@mkdir -p $(LOG_DIR)
	@sudo chown -R $$(id -u):$$(id -g) $(LOG_DIR) 2>/dev/null || true

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
	@if [ -z "$(SERVICE)" ]; then \
		echo "Usage: make logs-service SERVICE=<service-name>"; \
		echo "Example: make logs-service SERVICE=outpost"; \
	else \
		grep "^$(SERVICE)" $(LOG_DIR)/$$(date +%Y-%m-%d).log 2>/dev/null || echo "No logs for $(SERVICE)."; \
	fi

logs-search:
	@if [ -z "$(PATTERN)" ]; then \
		echo "Usage: make logs-search PATTERN='text'"; \
	else \
		grep -i "$(PATTERN)" $(LOG_DIR)/*.log 2>/dev/null || echo "Pattern '$(PATTERN)' not found"; \
	fi

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

down: logs-stop
	docker compose down --remove-orphans

update: down pull build
	echo "Proxy updated.  Bring it up with make up logs"

up: down ensureitems logdirs
	@# Generate versions.env from manifest if it exists
	@if [ -f "version-manifest.yaml" ]; then \
		python3 version-manager.py generate-env 2>/dev/null || true; \
	fi
	@# Start services with version env if available
	@if [ -f "versions.env" ]; then \
		set -a && . ./versions.env && set +a && \
		docker compose up -d; \
	else \
		docker compose up -d; \
	fi
	@echo "Starting background log capture..."
	@sleep 3
	@$(MAKE) logs-start

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
	@# Pull images from manifest if available, otherwise pull latest
	@if [ -f "version-manifest.yaml" ]; then \
		python3 version-manager.py pull-from-manifest; \
	else \
		python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/outpost:latest; \
		python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/cmd_exec:latest; \
		python3 docker-pull-retry.py hashicorp/vault:latest; \
	fi

# Pull latest images (updates manifest if versioning is enabled)
pull-latest:
	@if [ -f "version-manifest.yaml" ]; then \
		python3 version-manager.py pull-latest; \
	else \
		python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/outpost:latest; \
		python3 docker-pull-retry.py public.ecr.aws/n5k3t9x2/cmd_exec:latest; \
		python3 docker-pull-retry.py hashicorp/vault:latest; \
	fi

status:
	@python3 check-status.py

help:
	@echo "DagKnows Proxy Management Commands"
	@echo "==================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install      - Run the installation wizard"
	@echo ""
	@echo "Service Management:"
	@echo "  make up           - Start proxy services (+ auto log capture)"
	@echo "  make down         - Stop all services"
	@echo "  make status       - Check proxy status and versions"
	@echo "  make build        - Build Docker images"
	@echo "  make update       - Update to latest version"
	@echo "  make pull         - Pull images from manifest (or latest)"
	@echo "  make pull-latest  - Pull latest images (updates manifest)"
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
	@echo ""
	@echo "Version Management:"
	@echo "  make version           - Show current versions"
	@echo "  make help-version      - Show all version management commands"
	@echo ""
	@echo "Service Control (Recommended):"
	@echo "  make start        - Start all services (with log capture)"
	@echo "  make stop         - Stop all services and log capture"
	@echo "  make restart      - Restart all services"
	@echo ""
	@echo "Auto-Restart (System Boot):"
	@echo "  make setup-autorestart   - Setup auto-start on system reboot"
	@echo "  make disable-autorestart - Disable auto-start"
	@echo "  make autorestart-status  - Check auto-restart configuration"
	@echo "  make setup-log-rotation  - Setup daily log rotation"
	@echo "  make setup-versioning    - Setup version tracking"

# ==============================================
# SMART START/STOP/RESTART (Auto-detects mode)
# ==============================================

.PHONY: start stop restart setup-autorestart disable-autorestart autorestart-status

# Smart start: uses systemctl if auto-restart configured, otherwise traditional method
start: stop logdirs
	@if [ -f /etc/systemd/system/dkproxy.service ]; then \
		echo "Starting services via systemd (auto-restart mode)..."; \
		sudo systemctl start dkproxy.service; \
		sleep 3; \
		$(MAKE) logs-start; \
		echo "Done. Use 'make status' to check."; \
	else \
		echo "Starting services..."; \
		docker network create saaslocalnetwork 2>/dev/null || true; \
		if [ -f "version-manifest.yaml" ]; then \
			python3 version-manager.py generate-env 2>/dev/null || true; \
		fi; \
		if [ -f "versions.env" ]; then \
			set -a && . ./versions.env && set +a && \
			docker compose up -d; \
		else \
			docker compose up -d; \
		fi; \
		sleep 3; \
		$(MAKE) logs-start; \
		echo "Services started."; \
	fi

# Smart stop: stops all services and log capture
stop: logs-stop
	@echo "Stopping all services..."
	@if [ -f /etc/systemd/system/dkproxy.service ]; then \
		sudo systemctl stop dkproxy.service 2>/dev/null || true; \
	fi
	@docker compose down 2>/dev/null || true
	@echo "All services stopped."

# Smart restart
restart: stop start

# ==============================================
# AUTO-RESTART CONFIGURATION
# ==============================================

# Interactive auto-restart setup script (requires sudo)
setup-autorestart:
	@sudo bash setup-autorestart.sh

disable-autorestart:
	@echo "Disabling auto-restart..."
	@sudo systemctl stop dkproxy.service 2>/dev/null || true
	@sudo systemctl disable dkproxy.service 2>/dev/null || true
	@sudo rm -f /etc/systemd/system/dkproxy.service
	@sudo systemctl daemon-reload
	@echo "Auto-restart disabled."

autorestart-status:
	@echo "=== Auto-Restart Status ==="
	@if [ -f /etc/systemd/system/dkproxy.service ]; then \
		echo "Systemd service: INSTALLED"; \
		systemctl is-enabled dkproxy.service 2>/dev/null && echo "Service enabled: YES" || echo "Service enabled: NO"; \
		systemctl is-active dkproxy.service 2>/dev/null && echo "Service active: YES" || echo "Service active: NO"; \
	else \
		echo "Systemd service: NOT INSTALLED"; \
		echo "Run 'make setup-autorestart' to enable"; \
	fi

# ============================================
# STANDALONE SETUP SCRIPTS (for partial upgrades)
# ============================================

.PHONY: install setup-log-rotation setup-versioning

# Interactive installation wizard
install:
	@python3 install.py

# Interactive log rotation setup script
setup-log-rotation:
	@bash setup-log-rotation.sh

# Interactive versioning setup script
setup-versioning:
	@bash setup-versioning.sh

# ============================================
# VERSION MANAGEMENT
# ============================================

.PHONY: version version-history version-pull version-set rollback rollback-service rollback-to
.PHONY: update-safe check-updates resolve-tags migrate-versions generate-env help-version

# Show current versions
version:
	@python3 version-manager.py show

# Show version history
version-history:
	@python3 version-manager.py history $(SERVICE)

# Pull specific version for ONE service
# Usage: make version-pull SERVICE=outpost TAG=1.42
version-pull:
	@if [ -z "$(SERVICE)" ] || [ -z "$(TAG)" ]; then \
		echo "Error: SERVICE and TAG are required."; \
		echo "Usage: make version-pull SERVICE=outpost TAG=1.42"; \
		echo ""; \
		echo "Available services:"; \
		echo "  make version-pull SERVICE=outpost TAG=1.42"; \
		echo "  make version-pull SERVICE=cmd_exec TAG=1.15"; \
		echo "  make version-pull SERVICE=vault TAG=1.15.0"; \
		exit 1; \
	fi
	@python3 version-manager.py pull --service=$(SERVICE) --tag=$(TAG)

# Set custom version for hotfixes
# Usage: make version-set SERVICE=outpost TAG=1.42-hotfix
version-set:
	@if [ -z "$(SERVICE)" ] || [ -z "$(TAG)" ]; then \
		echo "Error: SERVICE and TAG are required."; \
		echo "Usage: make version-set SERVICE=outpost TAG=1.42-hotfix"; \
		exit 1; \
	fi
	@python3 version-manager.py set --service=$(SERVICE) --tag=$(TAG)

# Rollback all services to previous version
rollback:
	@python3 version-manager.py rollback --all

# Rollback specific service
# Usage: make rollback-service SERVICE=outpost
rollback-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE is required. Usage: make rollback-service SERVICE=outpost"; \
		exit 1; \
	fi
	@python3 version-manager.py rollback --service=$(SERVICE)

# Rollback to specific tag
# Usage: make rollback-to SERVICE=outpost TAG=1.41
rollback-to:
	@if [ -z "$(SERVICE)" ] || [ -z "$(TAG)" ]; then \
		echo "Error: SERVICE and TAG are required."; \
		echo "Usage: make rollback-to SERVICE=outpost TAG=1.41"; \
		exit 1; \
	fi
	@python3 version-manager.py rollback --service=$(SERVICE) --tag=$(TAG)

# Safe update to latest with automatic backup
update-safe:
	@python3 version-manager.py update-safe

# Check for available updates
check-updates:
	@python3 version-manager.py check-updates

# Resolve :latest tags to semantic versions
resolve-tags:
	@python3 version-manager.py resolve-tags

# Migrate existing deployment to versioned
migrate-versions:
	@python3 migrate-to-versioned.py

# Generate versions.env from manifest
generate-env:
	@python3 version-manager.py generate-env

# Friendly aliases
upgrade: update-safe
downgrade: rollback
whatversion: version

# Version management help
help-version:
	@echo "DagKnows Proxy Version Management"
	@echo "=================================="
	@echo ""
	@echo "NOTE: Each service has its own version"
	@echo "  - outpost: Proxy orchestration service (ECR)"
	@echo "  - cmd_exec: Command execution service (ECR)"
	@echo "  - vault: HashiCorp Vault (Docker Hub)"
	@echo ""
	@echo "View Versions:"
	@echo "  make version                         - Show current versions"
	@echo "  make version-history                 - Show history for all"
	@echo "  make version-history SERVICE=x       - Show history for service"
	@echo ""
	@echo "Update:"
	@echo "  make pull                            - Pull latest for all"
	@echo "  make update-safe                     - Safe update with backup"
	@echo "  make version-pull SERVICE=x TAG=y    - Pull specific version"
	@echo "  make version-set SERVICE=x TAG=y     - Set custom version (hotfix)"
	@echo "  make check-updates                   - Check for updates"
	@echo ""
	@echo "Rollback:"
	@echo "  make rollback                        - Rollback all to previous"
	@echo "  make rollback-service SERVICE=x      - Rollback specific service"
	@echo "  make rollback-to SERVICE=x TAG=y     - Rollback to specific version"
	@echo ""
	@echo "Migration:"
	@echo "  make migrate-versions                - Enable version tracking"
	@echo "  make generate-env                    - Regenerate versions.env"
	@echo "  make resolve-tags                    - Resolve :latest to versions"
	@echo ""
	@echo "Examples:"
	@echo "  make version-pull SERVICE=outpost TAG=1.42"
	@echo "  make version-set SERVICE=cmd_exec TAG=1.15-hotfix"
	@echo "  make rollback-service SERVICE=outpost"
	@echo ""
	@echo "Aliases:"
	@echo "  make upgrade      = make update-safe"
	@echo "  make downgrade    = make rollback"
	@echo "  make whatversion  = make version"
