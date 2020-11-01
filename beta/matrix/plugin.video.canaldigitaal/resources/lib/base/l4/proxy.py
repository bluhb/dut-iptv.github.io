import os, threading, time, xbmc, xbmcaddon

from resources.lib.base.l1.constants import ADDON_ID, ADDON_PATH, ADDON_PROFILE
from resources.lib.base.l2 import settings
from resources.lib.base.l3.util import force_highest_bandwidth, set_duration, load_profile, query_settings, remove_subs
from resources.lib.util import proxy_get_match, proxy_get_session, proxy_get_url, proxy_xml_mod

try:
    import http.server as ProxyServer
except ImportError:
    import BaseHTTPServer as ProxyServer

try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite

#from resources.lib.base.log import log

class HTTPMonitor(xbmc.Monitor):
    def __init__(self, addon):
        super(HTTPMonitor, self).__init__()
        self.addon = addon

class HTTPRequestHandler(ProxyServer.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self._stream_url
        except:
            profile_settings = load_profile(profile_id=1)
            self._stream_url = profile_settings['stream_hostname']

        try:
            self._last_playing
        except:
            self._last_playing = 0

        if "status" in self.path:
            self.send_response(200)
            self.send_header('X-TEST', 'OK')
            self.end_headers()

        elif proxy_get_match(self.path):
            profile_settings = load_profile(profile_id=1)
            self._stream_url = profile_settings['stream_hostname']

            URL = proxy_get_url(self)

            session = proxy_get_session(self)
            r = session.get(URL)

            xml = r.text

            xml = set_duration(xml=xml)

            if settings.getBool(key='disable_subtitle'):
                xml = remove_subs(xml=xml)

            if settings.getBool(key='force_highest_bandwidth'):
                xml = force_highest_bandwidth(xml=xml)

            xml = proxy_xml_mod(xml)

            self.send_response(r.status_code)

            r.headers['Content-Length'] = len(xml)

            for header in r.headers:
                if not 'Content-Encoding' in header and not 'Transfer-Encoding' in header:
                    self.send_header(header, r.headers[header])

            self.end_headers()

            try:
                xml = xml.encode('utf-8')
            except:
                pass

            try:
                self.wfile.write(xml)
            except:
                pass
        else:
            URL = proxy_get_url(self)

            self._now_playing = int(time.time())

            if self._last_playing + 60 < self._now_playing:
                self._last_playing = int(time.time())
                query = "UPDATE `vars` SET `last_playing`='{last_playing}' WHERE profile_id={profile_id}".format(last_playing=self._last_playing, profile_id=1)
                query_settings(query=query, return_result=False, return_insert=False, commit=True)

            self.send_response(302)
            self.send_header('Location', URL)
            self.end_headers()

    def log_message(self, format, *args):
        return

class HTTPServer(ProxyServer.HTTPServer):
    def __init__(self, addon, server_address):
        ProxyServer.HTTPServer.__init__(self, server_address, HTTPRequestHandler)
        self.addon = addon

class RemoteControlBrowserService(xbmcaddon.Addon):
    def __init__(self):
        super(RemoteControlBrowserService, self).__init__()
        self.pluginId = ADDON_ID
        self.addonFolder = ADDON_PATH
        self.profileFolder = ADDON_PROFILE
        self.settingsChangeLock = threading.Lock()
        self.isShutdown = False
        self.HTTPServer = None
        self.HTTPServerThread = None

    def clearBrowserLock(self):
        """Clears the pidfile in case the last shutdown was not clean"""
        browserLockPath = os.path.join(self.profileFolder, 'browser.pid')
        try:
            os.remove(browserLockPath)
        except OSError:
            pass

    def reloadHTTPServer(self):
        with self.settingsChangeLock:
            self.startHTTPServer()

    def shutdownHTTPServer(self):
        with self.settingsChangeLock:
            self.stopHTTPServer()
            self.isShutdown = True

    def startHTTPServer(self):
        if self.isShutdown:
            return

        self.stopHTTPServer()

        try:
            profile_settings = load_profile(profile_id=1)
            self.HTTPServer = HTTPServer(self, ('', int(profile_settings['proxyserver_port'])))
        except IOError as e:
            pass

        threadStarting = threading.Thread(target=self.HTTPServer.serve_forever)
        threadStarting.start()
        self.HTTPServerThread = threadStarting

    def stopHTTPServer(self):
        if self.HTTPServer is not None:
            self.HTTPServer.shutdown()
            self.HTTPServer = None
        if self.HTTPServerThread is not None:
            self.HTTPServerThread.join()
            self.HTTPServerThread = None