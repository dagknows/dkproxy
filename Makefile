
logs:
	sudo docker-compose logs -f

down:
	sudo docker-compose down --remove-orphans 

build: down ensureitems
	sudo docker-compose build --no-cache

up: down
	sudo docker-compose up -d

update: down download pull build up logs

download:
	wget https://github.com/dagknows/dkproxy/archive/refs/heads/main.zip
	unzip main.zip

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
