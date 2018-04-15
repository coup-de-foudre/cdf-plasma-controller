.PHONY: all
all:
	cd pigpio; make

.PHONY: install
install:
	cd pigpio; make install

.PHONY: service
service: install
	cd pigpio; cp pigpiod /etc/init.d/pigpiod \
	update-rc.d pigpiod defaults \
	service pigpiod start
