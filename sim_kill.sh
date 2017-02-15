#!/bin/bash

for pid in $(ps -ef | grep python\ diabetes_sim.py | awk '{print $2}'); do kill -9 $pid; done