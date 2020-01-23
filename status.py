# cython: language_level=3
import os
import os.path
import sys
import time
import datetime
import psutil
import fcntl
import signal
import netifaces
import threading
import requests
import socket

from Xlib import Xatom
from Xlib.display import Display
from collections import deque

def defaultnic():
    ret = None
    try:
        gws = netifaces.gateways()
        ret = gws['default'][2][1]
    except (IndexError, KeyError) as ex:
        return None
    return ret

def update_netinfo(rate, dt=1):
    t0 = time.time()
    counter = psutil.net_io_counters()
    tot = (counter.bytes_sent, counter.bytes_recv)

    while True:
        last_tot = tot
        time.sleep(dt)
        counter = psutil.net_io_counters()
        t1 = time.time()
        tot = (counter.bytes_sent, counter.bytes_recv)
        ul, dl = [(now - last) / (t1 - t0) / 1000.0
                  for now, last in zip(tot, last_tot)]
        rate.append((ul, dl))
        t0 = time.time()

def update_weather(weather, dt=300):

    APPID = '3e321f9414eaedbfab34983bda77a66e'  # 'borrowed' from awesomewm's lain library
    base_url = 'http://api.openweathermap.org/data/2.5/weather?'
    city_id = '4167147' # Orlando. Look yours up on openweathermap
    url = base_url + "appid=" + APPID + "&id=" + city_id

    then = int(time.time())
    while True:
        now = int(time.time())
        delta = now - then
        if delta > dt or delta == 0:
            try:
                weather.append(requests.get(url).json())
            except (ConnectionError) as ex:
                print(f"Can't connect: {ex}")
            then = now
        time.sleep(1)


def pctbar(value, maximum):

    bar = [ " ", "_", u"▁", u"▂", u"▃", u"▄", u"▅", u"▆", u"▇", u"█"]
    if value:
        pct = int(value / maximum * 100)
    else:
        return " "
    stackpos = abs(int(pct/(100/len(bar))) - 1)
    return bar[stackpos]

def getbatterypct():
    try:
        bat = open("/sys/class/power_supply/BAT0/capacity")
    except FileNotFoundError:
        return "-1"
    pct = bat.read()
    pct = pct.strip()
    return pct


def getbatstatus():
    try:
        bstat = open("/sys/class/power_supply/BAT0/status")
    except FileNotFoundError:
        return -1
    ret = bstat.read()
    ret = ret.strip()
    return ret

def getcpubars(cpulist):
    ret = ""
    for cpu in cpulist:
        ret += pctbar(cpu, 100)
    return ret

def degrees_to_cardinal(d):
    '''
    note: this is highly approximate...
    '''
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int((d + 11.25)/22.5)
    return dirs[ix % 16]

def createweatherstatus(weather):
    status = ''
    icons = {
            '01d': '🌞',
            '01n': '🌝',
            '02d': '⛅',
            '02n': '⛅',
            '03d': '☁',
            '03n': '☁',
            '04d': '☁',
            '04n': '☁',
            '09d': '🌧',
            '09n': '🌧',
            '10d': '🌦',
            '10n': '🌦',
            '11d': '🌩',
            '11n': '🌩',
            '13d': '❄',
            '13n': '❄',
            '50d': '🌫',
            '50n': '🌫',
    }

    city = weather['name']
    icon = icons[weather['weather'][0]['icon']]
    description = weather['weather'][0]['description']
    temp = int(weather['main']['temp'] - 273.15)
    if 'deg' in weather['wind']:
        winddir = degrees_to_cardinal(weather['wind']['deg'])
    else:
        winddir = "N/A"
    windspeed = str(weather['wind']['speed'])
    if windspeed == "1":
        windspeed = "no wind"
    else:
        windspeed += " m/s"
    status += city + " : " + \
            "Temp " + str(temp) + "C : "  \
            "Wind " + windspeed + " : " + winddir + " : " + \
            icon + " " + description  + " : "

    return status

def getinbox():
    auth = imap.config("auth")
    srv = imap.config("server")
    if auth == None or srv == None:
        return None

    try:
        msgs = imap.getmsgs(auth, srv, "INBOX")
        if msgs:
            if msgs > 1:
                status = f"📬 You have {msgs} unread messages!"
            else:
                status = f"📬 You have {msgs} unread message!"
        else:
            if msgs == 0:
                status = "📭 No new mail :("
            else:
                return None
    except KeyError as ex:
        return None

    return status

def getnowplaying():
    ph = player.getplayerhandle()
    if ph:
        songdata = player.getsongdata(ph)
    else:
        return None
    return songdata

def poll_player(nowplaying, dt=1):
    nowplaying.append("")
    while True:
        ret = getnowplaying()
        if ret:
            nowplaying.append(ret)
        else:
            nowplaying.append("")
        time.sleep(dt)


def poll_inbox(mailbox, dt=60):
    mailbox.append("")
    then = int(time.time())
    while True:
        now = int(time.time())
        delta = now - then
        if delta > dt or delta == 0:
            ret = getinbox()
            if ret:
                mailbox.append(ret)
            else:
                return None
            then = now
        time.sleep(1)


def main():

    display = Display()
    root = display.screen().root

    if 'imap' in sys.modules:
        # IMAP collection
        mailbox = deque(maxlen=1)
        m = threading.Thread(target=poll_inbox, args=(mailbox,))
        m.daemon
        m.start()
    else:
        mailbox = None

    if 'player' in sys.modules:
        # NowPlaying collection
        nowplaying = deque(maxlen=1)
        n = threading.Thread(target=poll_player, args=(nowplaying,))
        n.daemon
        n.start()
    else:
        nowplaying = [False]

    # Netstatus collection
    transfer_rate = deque(maxlen=1)
    t = threading.Thread(target=update_netinfo, args=(transfer_rate,))
    t.daemon = True
    t.start()

    # Weather collection
    weather_data = deque(maxlen=1)
    w = threading.Thread(target=update_weather, args=(weather_data,))
    w.daemon = True
    w.start()


    while(True):

        if os.path.isfile('/tmp/statquit'):
            os.unlink("/tmp/statquit")
            sys.exit()

        cpuload = psutil.cpu_percent(percpu=True)
        cpupct = getcpubars(cpuload)
        memused = psutil.virtual_memory().used // 1024 // 1024
        memtotal = psutil.virtual_memory().total // 1024 // 1024
        mempct = pctbar(memused, memtotal)
        swapused = psutil.swap_memory().used // 1024 // 1024
        swaptotal = psutil.swap_memory().total // 1024 // 1024
        swappct = pctbar(swapused, swaptotal)
        batpct = getbatterypct()
        batstatus = getbatstatus()
        now = datetime.datetime.now()
        curtime = now.strftime("%d-%m-%Y %H:%M:%S")
        nic = defaultnic()

        # Top bar
        status = ''

        if memtotal:
            status += f"Mem : {memused: >5}/{memtotal: >5} : "
        if swaptotal != 0:
            status += f"Swap : {swapused: >5}/{swaptotal: >5} : "
        if cpuload:
            status += f"CPU : {cpupct} : "
        if batstatus != -1:
            status += f"Battery : {batpct: >3}% ({batstatus: <11}) :"
        status += f" {curtime}"

        # Bottom bar
        status += ';'

        if nic:
            status += f'{nic: <8}: '
        try:
            status += 'Tx: {0:>9.0f} kB/s Rx: {1:>9.0f} kB/s : '.format(*transfer_rate[-1])
        except IndexError as ex:
            pass

        if weather_data:
            status += createweatherstatus(weather_data[-1])

        if mailbox:
            status += mailbox[-1]

        if nowplaying[-1]:
            status += ' : ' + nowplaying[-1]

        #root.set_wm_name(status)
        root.change_text_property(Xatom.WM_NAME, Xatom.STRING, status.encode("utf-8"),
                onerror = None)
        display.sync()
        time.sleep(1)


if __name__ == "__main__":
    main()
