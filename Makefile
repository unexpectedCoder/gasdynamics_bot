build:
	docker volume create labs && \
	docker volume create vault && \
	docker volume create db_data && \
	docker build -t gasdyn_bot_image .


run:
	docker run -it -d \
	--mount type=bind,src=./.env,dst=/usr/src/app/.env,readonly \
	--mount \
		type=bind,src=./students.json,dst=/usr/src/app/students.json,readonly \
	--mount source=db_data,target=/db_data \
	--mount source=labs,target=/labs \
	--mount source=vault,target=/vault \
	--name gasdyn_bot gasdyn_bot_image
attach:
	docker attach gasdyn_bot
stop:
	docker stop gasdyn_bot
rm:
	docker rm gasdyn_bot


rm_image:
	docker image rm gasdyn_bot_image
rm_labs:
	docker volume rm vault
rm_vault:
	docker volume rm vault
rm_db:
	docker volume rm db_data
rm_volumes:
	docker volume rm labs && \
	docker volume rm vault && \
	docker volume rm db_data
