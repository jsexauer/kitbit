# kitbit
Track the movement of your cat, dog, or other furry creature around your house


## Install (for Detectors on Raspberry PIs)
```commandline
git clone https://github.com/jsexauer/kitbit.git
cd kitbit/src
sudo apt-get install libbluetooth-dev python-dev libglib2.0-dev libboost-python-dev libboost-thread-dev
pip3 install -r requirements-detector.txt
# Give Bluetooth access to bluepy --> bluepy-helper 
sudo setcap 'cap_net_raw,cap_net_admin+eip' /home/pi/.local/lib/python3.9/site-packages/bluepy/bluepy-helper

# Test it works
python3 run_kitbit_detector.py

# Config to run at startup
sudo nano /etc/rc.local

# Navitage to bottom of file, add at end before "exit 0"
runuser -l pi -c 'python3 /home/pi/projects/kitbit/src/run_kitbit_detector.py &'
```

## Resources
Based on the work of: https://github.com/filipsPL/cat-localizer