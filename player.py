#!/usr/bin/python

import sys
from pprint import pprint

try:
    import mpris2
except ImportError as ex:
    print("You need mpris2 module!")
    sys.exit(1)

def getplayerhandle():
    uri = 'org.mpris.MediaPlayer2.google_play_music_desktop_player' # replace with your own player
    uri = 'org.mpris.MediaPlayer2.tuijam'
    try:
        player = mpris2.Player(dbus_interface_info={'dbus_uri': uri})
    except Exception as ex:
        return None

    return player

def getsongdata(player):
    try:
        metadata = player.Metadata
    except AttributeError as ex:
        print("No metadata! Is there a player active?")
        return None

    if metadata:
        artist = str(metadata['xesam:artist'][0])
        song = str(metadata['xesam:title'])
        album = str(metadata['xesam:album'])

        return f'{artist} - {song} ({album})'
    else:
        return None


def main():
    player = getplayerhandle()
    songdata = getsongdata(player)
    print(songdata)





if __name__ == "__main__":
    sys.exit(main())
