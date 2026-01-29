IMAGE_NAME ?= telegram_bot
IMAGE_TAG ?= latest

.PHONY: build run logs compose-up compose-down clean

build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

run:
	docker run --rm --env-file .env -it $(IMAGE_NAME):$(IMAGE_TAG)

logs:
	docker logs -f $(shell docker ps -q -f name=telegram_bot_app)

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

clean:
	docker image rm -f $(IMAGE_NAME):$(IMAGE_TAG) || true
	docker system prune -f || true

save:
	docker save -o $(IMAGE_NAME)-$(IMAGE_TAG).tar $(IMAGE_NAME):$(IMAGE_TAG)
	gzip -f $(IMAGE_NAME)-$(IMAGE_TAG).tar
