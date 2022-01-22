from time import sleep
from kitbit.detector.kitbit_detector import KitbitDetector

if __name__ == '__main__':
    print("Printing devices in a loop (every 15 seconds)")
    a = KitbitDetector()
    while True:
        a.print_all_devices()
        sleep(15)