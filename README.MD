After you have cloned the git repository, to run the program through a terminal do the following:

chmod +x start.sh

sudo ./start.sh

It will ask for a patient name and will save that value so it will only need to ask the once

If you want to then setup the program to autostart on a raspberry pi, do the following

chmod 775 startPi.sh

cd /

mkdir logs

sudo crontab -e

At the end of the file add:

@reboot sh "path to startPi.sh file" > /home/pi/logs/cronlog 2>&1

then press CTRL+X, Y, and then ENTER

After this, you should be good to reboot. The program will startup and use the patient name that was input earlier.
