#!/usr/bin/env python3

import os
import sys
import stat
import imaplib as imap
import configparser as cp

CONFIGFILE = os.getenv('HOME') + os.sep + ".config/imap.cfg"

def config(section):
    # Check if file is secure first.
    try:
        st = os.stat(CONFIGFILE)
        if st.st_mode != 0o100600:
            print(f"Insecure configfile. Not reading it. Bye! {oct(st.st_mode)}")
            sys.exit(1)
    except (FileNotFoundError, IOError) as ex:
        print(f"Can't open configfile: {ex}")
        return None

    conf = cp.ConfigParser()
    conf.read(CONFIGFILE)

    # Go through all the key/values in the section
    ret = {k:v for k,v in conf.items(section)}

    if not ret:
        print("No values?")
        return None

    return ret

def getmsgs(auth, srv, mailboxname):
    try:
        conn = imap.IMAP4_SSL(srv['host'], srv['port'])
        conn.login(auth['username'], auth['password'])
    except Exception as ex:
        print(f"Connect/Login failed! {ex}")
        return None
    conn.select(mailboxname)
    status, response = conn.search(None, '(UNSEEN)')
    unread = response[0].split()
    return len(unread)




def main():
    auth = config("auth")
    srv = config("server")
    msgs = getmsgs(auth, srv, "INBOX")

    if msgs:
        if msgs > 1:
            print(f"📬 You have {msgs} messages!")
        else:
            print(f"📬 You have {msgs} message!")
    else:
        print("📭 No new mail :(")



if __name__ == '__main__':
    sys.exit(main())

