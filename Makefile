
logs:
	sudo docker-compose logs -f

prepare:
	sudo apt-get update
	sudo apt-get install -y docker.io docker-compose unzip python-pip3

build: down ensureitems
	sudo docker-compose build --no-cache

down:
	sudo docker-compose down --remove-orphans 

update: down download pull build
	echo "Proxy updated.  Bring it up with make up logs"

up: down ensureitems
	sudo docker-compose up -d

download:
	rm -Rf main.zip proxy.tar.bz2 dkproxy-main
	wget https://github.com/dagknows/dkproxy/archive/refs/heads/main.zip
	unzip main.zip
	cd dkproxy-main ; tar -zcvf ../proxy.tar.bz2 .
	tar -zxvf proxy.tar.bz2
	rm -Rf main.zip proxy.tar.bz2 dkproxy-main

ensureitems:
	-mkdir -p ./outpost/sidecar/pyrunner
	-mkdir -p ./outpost/sidecar/statuses
	-sudo chmod -R a+rw ./outpost/sidecar
	-sudo chmod a+rx ./outpost/sidecar
	-sudo chmod a+rx ./outpost/sidecar/statuses
	-sudo chmod a+rx ./outpost/sidecar/pyrunner
	touch script_exec/requirements.txt
	touch outpost/requirements.txt
	touch cmd_exec/requirements.txt

pull:
	sudo docker pull gcr.io/dagknows-proxy-images/outpost:latest
	sudo docker pull gcr.io/dagknows-proxy-images/cmd_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/script_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/agent_frontend:latest
