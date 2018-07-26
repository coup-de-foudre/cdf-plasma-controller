IMAGE = plasma

.PHONY: docker test

test: docker
	docker run $(IMAGE) tox

docker: Dockerfile
	docker build -t $(IMAGE) .
