volumes:
	docker volume create labs && \
	docker volume create vault && \
	docker volume create db_data
build:
	docker build -t unexpectedcoder/gasdyn_bot_image .


run:
	docker run -it -d \
	--mount type=bind,src=./secrets,dst=/usr/src/app/secrets,readonly \
	--mount source=db_data,target=/db_data \
	--mount source=labs,target=/labs \
	--mount source=vault,target=/vault \
	--name gasdyn_bot unexpectedcoder/gasdyn_bot_image
attach:
	docker attach gasdyn_bot
stop:
	docker stop gasdyn_bot
rm:
	docker rm gasdyn_bot

rm_image:
	docker image rm unexpectedcoder/gasdyn_bot_image

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
