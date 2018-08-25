#!/usr/bin/env bash

# Suba, XENON + C
XC_IP="192.168.1.11"
XC_CH="pwm1"
XC_CENTER=60500
XC_SPREAD=9500
XC_FLAGS="-f ${XC_CENTER} -S ${XC_SPREAD}"

# ARGON, KRYPTON, IODINE (blue)
AKI_IP="192.168.1.12"
AKI_CH="pwm2"
AKI_CENTER=29350
AKI_SPREAD=4350
AKI_FLAGS="-f ${AKI_CENTER} -S ${AKI_SPREAD}"

# ARGON, KRYPTON, NEON (red/white)
AKN_IP="192.168.1.13"
AKN_CH="pwm3"
AKN_CENTER=27250
AKN_SPREAD=3250
AKN_FLAGS="-f ${AKN_CENTER} -S ${AKN_SPREAD}"

# ARGON prototype (purple)
AP_IP="192.168.1.14"
AP_CH="pwm4"
AP_CENTER=25500
AP_SPREAD=1500
AP_FLAGS="-f ${AP_CENTER} -S ${AP_SPREAD}"


USER="pi"
KILL="killall python3"
PC="/home/${USER}/cdf-plasma-controller/plasma_controller.py --controller OSC -vvv"

XC_CMD="${KILL} && nohup ${PC} ${XC_FLAGS} > out.log 2>&1  < /dev/null &"
#ssh -n -f ${USER}@${XC_IP} "${XC_CMD}"

AKI_CMD="${KILL} && nohup ${PC} ${AKI_FLAGS} > out.log 2>&1 &"
ssh -n -f -vvv ${USER}@${AKI_IP} "${AKI_CMD}"

AKN_CMD="${KILL} && nohup ${PC} ${AKN_FLAGS} > out.log 2>&1 &"
#ssh -n -f ${USER}@${AKN_IP} "${AKN_CMD}"

AP_CMD="${KILL} && nohup ${PC} ${AP_FLAGS} 2>&1 > out.log &"
#ssh -n -f ${USER}@${AP_IP} "${AP_CMD}"
