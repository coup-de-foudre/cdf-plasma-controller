IMAGE = plasma

.PHONY: docker test

test: docker
	docker run $(IMAGE) tox

docker: Dockerfile
	docker build -t $(IMAGE) .

.PHONY: pigpio-daemon
pigpio-daemon:
	sudo cp pigpio/util/pigpiod /etc/init.d
	sudo chmod +x /etc/init.d/pigpiod
	sudo update-rc.d pigpiod defaults
	sudo service pigpiod start

.PHONY: pigpio
pigpio:
	cd pigpio; make && sudo make install

.PHONY: daemon
daemon: pigpio-daemon
	sudo cp ./deploy/plasma_controller.service /lib/systemd/system/plasma_controller.service
	sync
	sudo systemctl daemon-reload
	sudo systemctl enable plasma_controller
	sudo systemctl start plasma_controller

.PHONY: logs
logs:
	sudo journalctl --follow -n 50 _SYSTEMD_UNIT=plasma_controller.service

.PHONY: player-logs
player-logs:
	sudo journalctl --follow -n 50 _SYSTEMD_UNIT=plasma_player.service

# Full on-Pi update: pip install, install/refresh both systemd units, reload,
# enable, restart. Intended to be run after `git pull` on a deployed Pi.
.PHONY: deploy
deploy:
	sudo pip3 install -r requirements.txt
	sudo cp ./deploy/plasma_controller.service /lib/systemd/system/plasma_controller.service
	sudo cp ./deploy/plasma_player.service /lib/systemd/system/plasma_player.service
	sync
	sudo systemctl daemon-reload
	sudo systemctl enable plasma_controller plasma_player
	sudo systemctl restart plasma_controller plasma_player

# Laptop-side fleet updater. Runs `git pull && sudo make deploy` on each Pi
# defined in config/irobot.conf. Pass tube names (e.g. `pwm1 pwm3`) to limit
# the rollout, or no args to update all.
.PHONY: fleet-update
fleet-update:
	./scripts/update_fleet.sh $(filter-out $@,$(MAKECMDGOALS))
