import xbmc
import xbmcgui
import subprocess
import socket
import requests
from contextlib import closing

class SopCastPlayer(xbmc.Player):
    def __init__(self, engine, env):
        xbmc.Player.__init__(self)
        self.env = env
        if type(engine) == list:
            self.engine = engine
        else:
            self.engine = [engine]
        self.localport = self.find_free_port()
        self.playerport = self.find_free_port()
        self.url = 'http://localhost:{0}'.format(self.playerport)
        self.running = False

    def playChannel(self, channel_url, timeout):
        self.start_sopcast(channel_url)
        self.start_session(timeout)
        if self.running:
            li = xbmcgui.ListItem('SopCast')
            li.setInfo('video', {'Title': 'SopCast'})
            self.play(self.url, li)
            # keep class alive until playback
            while not self.isPlaying():
                xbmc.sleep(300)
            # keep class alive during playback
            while self.isPlaying():
                xbmc.sleep(500)
            self.close_sopcast()

    @staticmethod
    def find_free_port():
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind(('localhost', 0))
            return str(s.getsockname()[1])

    def start_sopcast(self, channel_url):
        command = self.engine + [channel_url, self.localport, self.playerport]
        self.sopcast = subprocess.Popen(command, env=self.env)
        self.running = True

    def start_session(self,timeout):
        pDialog = xbmcgui.DialogProgress()
        pDialog.create('SopCast')

        session = requests.session()

        for i in xrange(int(timeout)):
            pDialog.update(int(i/float(timeout)*100))
            if pDialog.iscanceled():
                self.close_sopcast()
                break
            try:
                _r = session.get(self.url, stream=True, timeout=1)
                _r.raise_for_status()
                break
            except Exception:
                if i == int(timeout):
                    self.close_sopcast()
                else:
                    xbmc.sleep(1000)

        session.close()
        pDialog.close()

    def close_sopcast(self):
        try:
            # terminate does not work
            self.sopcast.kill()
            # prevent GC zombies
            self.sopcast.wait()
            self.running = False
        except OSError:
            # sopcast process already dead
            pass
