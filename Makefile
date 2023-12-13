
logs:
	docker compose logs -f

prepare:
	sudo apt-get update
	sudo apt-get install -y make docker.io docker compose unzip python-pip3 docker-compose-plugin
	echo "Installing Docker Repos..."
	sudo apt-get install ca-certificates curl gnupg
	sudo install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
	sudo chmod a+r /etc/apt/keyrings/docker.gpg
	echo "Adding the repository to Apt sources..."
	echo \
		"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
		$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
		sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
	echo "Adding user to docker user group..."
	sudo usermod -aG docker ${USER}

build: down ensureitems
	docker compose build --no-cache

down:
	docker compose down --remove-orphans 

update: down download pull build
	echo "Proxy updated.  Bring it up with make up logs"

up: down ensureitems
	docker compose up -d

download:
	rm -Rf main.zip proxy.tar.bz2 dkproxy-main
	wget https://github.com/dagknows/dkproxy/archive/refs/heads/main.zip
	unzip main.zip
	cd dkproxy-main ; tar -zcvf ../proxy.tar.bz2 .
	tar -zxvf proxy.tar.bz2
	rm -Rf main.zip proxy.tar.bz2 dkproxy-main

ensureitems:
	touch script_exec/requirements.txt
	touch outpost/requirements.txt
	touch cmd_exec/requirements.txt
	-mkdir -p ./outpost/sidecar/pyrunner
	-mkdir -p ./outpost/sidecar/statuses
	-sudo chmod -R a+rw ./outpost/sidecar
	-sudo chmod a+rx ./outpost/sidecar ./outpost/sidecar/statuses ./outpost/sidecar/pyrunner
	-sudo chmod -R a+rwx script_exec/jobs
	-sudo chmod -R a+rwx cmd_exec/jobs
	-sudo chmod -R a+rwx outpost/jobs
	-sudo chmod -R a+rwx outpost/logs
	-sudo chmod -R a+rwx vault/data

pull:
	docker pull gcr.io/dagknows-proxy-images/outpost:latest
	docker pull gcr.io/dagknows-proxy-images/cmd_exec:latest
	docker pull gcr.io/dagknows-proxy-images/script_exec:latest
	docker pull gcr.io/dagknows-proxy-images/agent_frontend:latest
