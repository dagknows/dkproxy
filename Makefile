
logs:
	docker compose logs -f

prepare:
	sudo apt-get update
	sudo apt-get install -y make docker.io docker docker-compose unzip python3-pip docker-compose-v2
	echo "Installing Docker Repos..."
	sudo apt-get install ca-certificates curl gnupg
	sudo install -m 0755 -d /etc/apt/keyrings
	@if [ ! -f /etc/apt/keyrings/docker.gpg ]; then \
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg ; \
	fi
	echo "Adding user to docker user group..."
	sudo usermod -aG docker ${USER}
	sudo chmod a+r /etc/apt/keyrings/docker.gpg
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

up: down ensureitems
	docker compose up -d

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
	docker pull gcr.io/dagknows-proxy-images/outpost:latest
	docker pull gcr.io/dagknows-proxy-images/cmd_exec:latest
