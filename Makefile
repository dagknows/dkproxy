
logs:
	sudo docker-compose logs -f

down:
	sudo docker-compose down --remove-orphans 

build: down
	sudo docker-compose build --no-cache

up: down
	sudo docker-compose up -d

update: down pull build up logs

pull:
	sudo docker pull gcr.io/dagknows-proxy-images/outpost:latest
	sudo docker pull gcr.io/dagknows-proxy-images/cmd_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/script_exec:latest
	sudo docker pull gcr.io/dagknows-proxy-images/agent_frontend:latest
	touch script_exec/requirements.txt
	touch outpost/requirements.txt
	touch cmd_exec/requirements.txt
