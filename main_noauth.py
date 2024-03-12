import network
import socket
import time
import select
import ure

from machine import Pin

led = Pin("LED", Pin.OUT)
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
        print( 'ip = ' + status[0] )

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
                request = ""

                cl_file = cl.makefile('rwb', 0)
                while True:
                    line = cl_file.readline()
                    request = request + str(line)
                    if not line or line == b'\r\n':
                        break

                url = ure.search(r"GET (/\S*) HTTP", request)

                if url:
                    servePage(cl, url.group(1))
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
    sleep.value(1)
    for x in range(1600):
        step.value(1)
        time.sleep_us(250)
        step.value(0)
        time.sleep_us(250)
        if x % 100 == 0:
            led.toggle()
    led.high()
    print('kibble dispensed')

def servePage(cl, url):
    if url == "/dispense":
        dispense()
        cl.send('HTTP/1.0 200 OK\r\nContent-type: application/json\r\n\r\n{"status":"Kibbles dispensed!"}')
    elif url == "/":
        page = open("index.html", "r")
        
        cl.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        for line in page.read():
            cl.send(line)

        page.close()
    else:
        cl.send('HTTP/1.0 404 Not Found\r\n\r\n')

connectWifi()
handleWebRequest()