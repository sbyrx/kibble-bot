# This version of main.py is designed to sit behind a CloudFlare Zero-Trust tunnel
# and keep track of how many kibbles each authenticated user has dispensed. It limits 
# the number of kibbles a user can dispense to one per week. The idea is to be able
# to open up access to the KibbleBot to friends and family.

import network
import socket
import time
import select
import ure
import json
import ntptime

from machine import Pin

led = Pin('LED', Pin.OUT)
dir = Pin(15, Pin.OUT)
step = Pin(14, Pin.OUT)
sleep = Pin(13, Pin.OUT)
button = Pin(10, Pin.IN, Pin.PULL_UP)

led.low()
sleep.low()
dir.low()
step.low()

ssid = 'SSID'
password = 'PASSWORD'

database = dict()

# These users are not limited to once per week and can dispense unlimited kibbles
allowlist = ['myemail@domain.com']

# Connect Pi to WiFi
def connectWifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('connecting to wifi...')
        time.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        ntptime.settime()
        print('current time is ' + str(time.localtime()))


 # Listen for HTTP requests
def handleWebRequest():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    cl = socket.socket()
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    print('listening on', addr)
    led.high()

    while True:
        try:
            poller = select.poll()
            poller.register(s, select.POLLIN)
            res = poller.poll(100)

            if res:
                cl, addr = s.accept()
                print('client connected from', addr)
                request = ''

                cl_file = cl.makefile('rwb', 0)
                while True:
                    line = cl_file.readline()
                    request = request + str(line)
                    if not line or line == b'\r\n':
                        break

                url = ure.search(r'GET (/\S*) HTTP', request)
                email = ure.search(r'Cf-Access-Authenticated-User-Email: (\S*)\\r\\n', request)

                if url and email:
                    servePage(cl, url.group(1), email.group(1))
                else:
                    cl.send('HTTP/1.0 400 Bad Request\r\n\r\n')
                
                cl.close()
            
            # In between waiting for web requests, check if the dispense button has been pressed
            if button.value() == 0:
                print('button pressed')
                dispense()

        except OSError as e:
            cl.close()
            s.close()
            print('connection closed')

def dispense():
    print('dispensing kibble')
    sleep.high()
    for x in range(1600):
        step.value(1)
        time.sleep_us(250)
        step.value(0)
        time.sleep_us(250)
        if x % 100 == 0:
            led.toggle()
    led.high()
    sleep.low()
    print('kibble dispensed')

def loadDatabase():
    databaseFile = open('database.json', 'r')
    database = json.loads(databaseFile.read())
    databaseFile.close()
    return database


def saveDatabase():
    databaseFile = open('database.json', 'w')
    databaseFile.write(json.dumps(database))
    databaseFile.flush()
    databaseFile.close()

def canDispense(email):
    if email not in database:
        database[email] = 0

    if email in allowlist:
        database[email] = database[email] + 1
        return True;

    year, month, mday, hour, minute, second, weekday, yearday = time.localtime()
    weekNumber = yearday/7

    if database[email] <= weekNumber:
        database[email] = database[email] + 1
        return True
    return False

def servePage(cl, url, email):
    if url == '/dispense':
        if canDispense(email):
            dispense()
            saveDatabase()
            print(email + ' dispensed kibble #' + str(database[email]))
            cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n{"status":"Kibbles dispensed!", "kibblesDispensed":"' + str(database[email]) + '"}')
        else:
            cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n{"status":"You have no more kibbles left to give!", "kibblesDispensed":"' + str(database[email]) + '"}')
    elif url == '/':
        page = open('index.html', 'r')
        
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        for line in page.read():
            cl.send(line)

        page.close()
    elif url == '/stats' and email in allowlist:
        cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n' + json.dumps(database))
    else:
        cl.send('HTTP/1.0 404 Not Found\r\n\r\n')

database = loadDatabase()
connectWifi()
handleWebRequest()