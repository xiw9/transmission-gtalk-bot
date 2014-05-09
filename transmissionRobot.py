#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import logging
import sys, os, datetime
import traceback
import transmissionrpc

from pyxmpp2.jid import JID
from pyxmpp2.message import Message
from pyxmpp2.presence import Presence
from pyxmpp2.client import Client
from pyxmpp2.settings import XMPPSettings
from pyxmpp2.interfaces import EventHandler, event_handler, QUIT
from pyxmpp2.streamevents import AuthorizedEvent, DisconnectedEvent
from pyxmpp2.interfaces import XMPPFeatureHandler
from pyxmpp2.interfaces import presence_stanza_handler, message_stanza_handler
from pyxmpp2.ext.version import VersionProvider
from pyxmpp2.mainloop.interfaces import TimeoutHandler,timeout_handler

from settings import *
__version__ = '0.1'

class transmissionRobot(EventHandler, XMPPFeatureHandler, TimeoutHandler):
    userlist={};
    lastcycle={};
    def __init__(self, my_jid, settings):
        version_provider = VersionProvider(settings)
        self.client = Client(my_jid, [self, version_provider], settings)
        self.rpc=transmissionrpc.Client(TRANSURL,TRANSPORT,TRANSUSER,TRANSPASS)
        for user in SUBSCRIBERS:
            self.userlist[JID(user).local]=JID(user)
        
    def run(self):
        """Request client connection and start the main loop."""
        self.client.connect()
        self.client.run()

    def disconnect(self):
        """Request disconnection and let the main loop run for a 2 more
        seconds for graceful disconnection."""
        self.client.disconnect()
        self.client.run(timeout = 2)

    @presence_stanza_handler("subscribe")
    def handle_presence_subscribe(self, stanza):
        logging.info(u"{0} requested presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "subscribe")
        return [stanza.make_accept_response(), presence]

    @presence_stanza_handler("subscribed")
    def handle_presence_subscribed(self, stanza):
        logging.info(u"{0!r} accepted our subscription request"
                                                    .format(stanza.from_jid))
        return True

    @presence_stanza_handler("unsubscribe")
    def handle_presence_unsubscribe(self, stanza):
        logging.info(u"{0} canceled presence subscription"
                                                    .format(stanza.from_jid))
        presence = Presence(to_jid = stanza.from_jid.bare(),
                                                    stanza_type = "unsubscribe")
        return [stanza.make_accept_response(), presence]

    @presence_stanza_handler("unsubscribed")
    def handle_presence_unsubscribed(self, stanza):
        logging.info(u"{0!r} acknowledged our subscrption cancelation"
                                                    .format(stanza.from_jid))
        return True

    @message_stanza_handler()
    def handle_message(self, stanza):
        messagebody='Robot connected.'
        if stanza.body=="connect":
            if not stanza.from_jid.local in self.userlist:
                self.userlist[stanza.from_jid.local]=stanza.from_jid;
            else:
                messagebody="Already connected."
            msg = Message(stanza_type = stanza.stanza_type,
                        from_jid = self.client.jid, to_jid = stanza.from_jid,
                        subject = None, body = messagebody,
                        thread = stanza.thread)
            return msg
        elif stanza.body=="disconnect":
            messagebody="Robot disconnected."
            try:
                del self.userlist[stanza.from_jid.local];
            except:
                messagebody="Already disconnected"
            msg = Message(stanza_type = stanza.stanza_type,
                        from_jid = self.client.jid, to_jid = stanza.from_jid,
                        subject = None, body = messagebody,
                        thread = stanza.thread)
            return msg
        
        if stanza.from_jid.local+'@'+stanza.from_jid.domain in SUBSCRIBERS:
            try:
                #print stanza.body
                torrent=self.rpc.add_torrent(stanza.body,timeout=10)
            except:
                return True
            messagebody="Torrent added: "+str(torrent)
            msg = Message(stanza_type = stanza.stanza_type,
                        from_jid = self.client.jid, to_jid = stanza.from_jid,
                        subject = None, body = messagebody,
                        thread = stanza.thread)
            return msg
        return True

    @event_handler(DisconnectedEvent)
    def handle_disconnected(self, event):
        """Quit the main loop upon disconnection."""
        return QUIT
        
    
    @event_handler()
    def handle_all(self, event):
        """Log all events."""
        logging.info(u"-- {0}".format(event))
        
    @timeout_handler(3,True)
    def handle_transmission_query(self):
        print "Checking transmission daemon."
        torrentlist=self.rpc.get_torrents()
        for torrent in torrentlist:
            if torrent.doneDate>0 and torrent.hashString in self.lastcycle:
                del self.lastcycle[torrent.hashString]
                messagebody="Torrent finished: "+ torrent.name + ". https://cloud.xiw.im/index.php/apps/files?dir=/Transmission"
                print messagebody
                for i in self.userlist:
                    msg = Message(stanza_type = "normal",
                        from_jid = self.client.jid, to_jid = self.userlist[i],
                        subject = None, body = messagebody,
                        thread = None)
                    self.client.send(msg)
            elif torrent.doneDate<=0 and not torrent.hashString in self.lastcycle:
                self.lastcycle[torrent.hashString]=1
        return 3
        
if __name__ == '__main__':
    
    logging.basicConfig(level = 0)
    handler = logging.StreamHandler()
    if TRACE:
        handler.setLevel(logging.DEBUG)
        for logger in ("pyxmpp2.IN", "pyxmpp2.OUT"):
            logger = logging.getLogger(logger)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.propagate = False
        
    my_jid = JID(USER+'/bot')
    settings = XMPPSettings({
                        "software_name": "Transmission Robot",
                        "tls_verify_peer": False,
                        "starttls": True,
                        "ipv6":False,
                        })
    settings["password"] = PASS

    bot = transmissionRobot(my_jid, settings)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.disconnect()

