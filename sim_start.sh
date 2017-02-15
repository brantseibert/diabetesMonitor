#!/bin/bash

for x in {1..10}; do (python diabetes_sim.py -e a97s39tib3rs1.iot.us-west-2.amazonaws.com -r root-CA.crt -C us-west-2:fc5a00da-47a0-4070-a8e9-25c5a6f1d398 -u $x > /tmp/$x.log ) & done