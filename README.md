# kitbit
Track the movement of your cat, dog, or other furry creature around your house


## Install
```commandline
sudo apt-get install libbluetooth-dev python-dev libglib2.0-dev libboost-python-dev libboost-thread-dev
pip3 install -r requirements.txt
# Give Bluetooth access to bluepy --> bluepy-helper 
sudo setcap 'cap_net_raw,cap_net_admin+eip' /home/pi/.local/lib/python3.9/site-packages/bluepy/bluepy-helper
```

## Resources
Based on the work of: https://github.com/filipsPL/cat-localizer