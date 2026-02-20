DC = docker compose

.PHONY: build up run stop rm down logs ps shell rm_image

build:
	$(DC) build

up:
	$(DC) up -d

run: up

stop:
	$(DC) stop

rm:
	$(DC) rm -f

down:
	$(DC) down

logs:
	$(DC) logs -f --tail=200

ps:
	$(DC) ps

shell:
	$(DC) exec gasdyn_bot sh

rm_image:
	docker image rm unexpectedcoder/gasdyn_bot_image
