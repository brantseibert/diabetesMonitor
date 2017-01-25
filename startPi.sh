# stop script on error
set -e

cd /
cd home/pi/Documents/Ascentti/Ascentti-Diabetes

# Wait for the network to start
sleep 10

# Update the source code for the diabetes simulator
git pull

# Check to see if root CA file exists, download if not
if [ ! -f ./root-CA.crt ]; then
  printf "\nDownloading AWS IoT Root CA certificate from Symantec...\n"
  curl https://www.symantec.com/content/en/us/enterprise/verisign/roots/VeriSign-Class%203-Public-Primary-Certification-Authority-G5.pem > root-CA.crt
fi

# install AWS Device SDK for Python if not already installed
if [ ! -d ./aws-iot-device-sdk-python ]; then
  printf "\nInstalling AWS SDK...\n"
  git clone https://github.com/aws/aws-iot-device-sdk-python.git
  pushd aws-iot-device-sdk-python
  python setup.py install
  popd
fi

# Run the Diabetes Simulation using the Cognito access
printf "\nRunning the Diabetes Monitor Simulation...\n"
python diabetes_sim.py -e a97s39tib3rs1.iot.us-west-2.amazonaws.com -r root-CA.crt -C us-west-2:fc5a00da-47a0-4070-a8e9-25c5a6f1d398

cd /