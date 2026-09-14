import serial

ser = serial.Serial("COM7", 9600, timeout=1)

try:
    while True:
        line = ser.readline().decode("utf-8").strip()
        if line:
            print("Изменение:", line)
except KeyboardInterrupt:
    ser.close()