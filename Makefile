IMAGE = plasma

.PHONY: docker test

test: docker
	docker run $(IMAGE) tox

docker: Dockerfile
	docker build -t $(IMAGE) .

.PHONY: daemon
daemon:
	sudo cp ./deploy/plasma_controller.service /lib/systemd/system/plasma_controller.service
	sync
	sudo systemctl daemon-reload
	sudo systemctl enable plasma_controller
	sudo systemctl start plasma_controller

.PHONY: logs
logs:
	sudo journalctl --follow -n 50 _SYSTEMD_UNIT=plasma_controller.service
