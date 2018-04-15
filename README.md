# CdF Plasma Controller

Raspberry Pi-based PWM controller for plasma tubes.


## Installation


### On the Raspberry Pi

Clone the repository.

```
cd ~/
git clone git@github.com:coup-de-foudre/cdf-plasma-controller.git
cd cdf-plasma-controller/
```


#### Install `python3` with `pip` and the requirements

We require Python3 and pip, which you have to install:

```
sudo apt-get update && sudo apt-get install -y python3-pip
sudo pip3 install -r requirements.txt
```

#### Install `pigpio` from source and start the daemon

The CdF Plasma Controller includes the `pigpio` installation and  requires
that the `pigpiod` daemon. To install the daemon and have it run on startup,
use

    make && sudo make install && sudo make service

You can now start, stop and restart the `pigpiod` service using the commands

```
sudo service pigpiod start
sudo service pigpiod stop
sudo service pigpiod restart
```

See the [pigpio README](./pigpio/README) for more details.


### On a client machine external to the Raspberry Pi

If you want to run over a network, you'll need to have Python 3.4 or greater 
(preferably 3.6) and `pip3` installed on the client machine. (Google it.) Then
clone this repo and run

```
pip3 install -r requirments.txt
```

You should now be able to connect to a remote Raspberry Pi running the
`pigpiod` daemon. 


## Running

For the full range of options, use `./plasma_controller.py -h`.


### Examples

1. To run an uninterrupted PWM locally at 1000 Hz: 

    ```
    ./plasma_controller.py -f 1000.0
    ```

1. Run over a network on pin 12 at 15kHz.

    ```
    ./plasma_controller.py --pin 12 --host 192.168.2.247 -f 15000
    ```

1. Run in interrupted mode, with the interrupter running at 100Hz and 30% duty 
cycle.

    ```
    ./plasma_controller.py -F 100 -D 0.3 -f 30000
    ```

> **NOTE** Running interruption over a network is not recommended, since network
> latency will significantly affect the interruption rate.


## Copyright and License

    Copyright 2018, Michael McCoy <michael.b.mccoy@gmail.com>
    
    This file is part of the CdF Plasma Controller.
    
    The CdF Plasma Controller is free software: you can redistribute it and/or 
    modify it under the terms of the GNU Affero General Public License as 
    published by the Free Software Foundation, either version 3 of the License, 
    or (at your option) any later version.
    
    CdF Plasma Controller is distributed in the hope that it will be useful, 
    but WITHOUT ANY WARRANTY; without even the implied warranty of 
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero
    General Public License for more details.
    
    You should have received a copy of the GNU Affero General Public License
    along with the Cdf Plasma Controller.  If not, see 
    <http://www.gnu.org/licenses/>.
