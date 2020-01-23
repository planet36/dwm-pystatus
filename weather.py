#!/usr/bin/env python3

import sys
import json
import requests

APPID = '3e321f9414eaedbfab34983bda77a66e'  # 'borrowed' from awesomewm's lain library
base_url = 'http://api.openweathermap.org/data/2.5/weather?'
city_id = '2757345' # Delft. Look yours up on openweathermap
url = base_url + "appid=" + APPID + "&id=" + city_id

def main():
    weather = requests.get(url).json()
    print(json.dumps(weather, indent=4, sort_keys=True))


if __name__ == '__main__':
    sys.exit(main())
