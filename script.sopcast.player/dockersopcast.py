import xbmc
import xbmcgui
import subprocess
import socket
import requests
from contextlib import closing

CREATE_NO_WINDOW = 0x08000000

class DockerSopCastPlayer(xbmc.Player):
    def __init__(self, container):
        xbmc.Player.__init__(self)
        self.container = container
        self.localport = self.find_free_port()
        self.playerport = self.find_free_port()
        self.url = 'http://localhost:{0}'.format(self.playerport)
        self.image = 'sopcast_{0}'.format(self.playerport)
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
        command = ['docker', 'run', '-d', '--name', self.image, '-p', '{0}:{0}'.format(self.playerport), self.container, channel_url, self.playerport]
        self.sopcast = subprocess.Popen(command, creationflags=CREATE_NO_WINDOW)
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
        command_stop = ['docker', 'stop', self.image]
        command_rm = ['docker', 'rm', self.image]
        stop = subprocess.Popen(command_stop, creationflags=CREATE_NO_WINDOW)
        stop.wait()
        rm = subprocess.Popen(command_rm, creationflags=CREATE_NO_WINDOW)
        rm.wait()