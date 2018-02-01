import sys,re,os
import urlparse
import xbmc
import xbmcaddon
import xbmcplugin
import sopclient
import dockersopcast
import shutil,stat
import platform
import subprocess


addon = xbmcaddon.Addon()
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

ADDON_DATA_DIR = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
RESOURCES_DIR = os.path.join(ADDON_DATA_DIR, 'resources')
BIN_DIR = os.path.join(RESOURCES_DIR, 'bin')
ANDROID_OLD = os.path.join(BIN_DIR, 'android_old')
ANDROID_OLD_SOPCLIENT = os.path.join(ANDROID_OLD, 'sopclient')
LINUX_X86 = os.path.join(BIN_DIR, 'linux_x86')
LINUX_X86_SOPCLIENT = os.path.join(LINUX_X86, 'sp-sc-auth')
LINUX_ARM = os.path.join(BIN_DIR, 'linux_arm')
LINUX_ARM_LD = os.path.join(LINUX_ARM, "lib", "ld-linux.so.2")
LINUX_ARM_SOPCLIENT = os.path.join(LINUX_ARM, 'sp-sc-auth')
LINUX_ARM_QEMU_SOPCLIENT = os.path.join(LINUX_ARM, 'qemu-i386')
LINUX_A64_QEMU_SOPCLIENT = os.path.join(LINUX_ARM, 'qemuaarch-i386')
SOP_ACTIVITY = ''
ENGINE = ''
DOCKER = ''
ENV = {}

url = args.get('url', None)[0]
timeout = args.get('timeout', ['100'])[0]

def log(msg):
    xbmc.log(("[%s] %s" % ('SopCast', msg)).encode('utf-8'), level=xbmc.LOGNOTICE)

def is_exe(fpath):
    if os.path.isfile(fpath):
        if (os.access(fpath, os.X_OK) != True) :
            st = os.stat(fpath)
            os.chmod(fpath, st.st_mode | stat.S_IEXEC)

def test_exe(engine, env):
    process = subprocess.Popen(engine,env=env,stdout=subprocess.PIPE)
    info = process.stdout.readline()
    log(info)
    process.wait()

def get_android_old_sopcast():
    def find_apk_id():
        xbmcfolder=xbmc.translatePath(ADDON_DATA_DIR).split("/")
        for folder in xbmcfolder:
            if folder.count('.') >= 2 and folder != addon_handle :
                return folder

    xbmc_data_path = os.path.join("/data", "data", find_apk_id())
    android_binary_dir = os.path.join(xbmc_data_path, "files", "script.sopcast.player")
    if not os.path.exists(android_binary_dir):
        os.makedirs(android_binary_dir)
    android_binary_path = os.path.join(android_binary_dir, "sopclient")
    if not os.path.exists(android_binary_path):
        shutil.copy2(ANDROID_OLD_SOPCLIENT, android_binary_path)
    is_exe(android_binary_path)
    return android_binary_path

if url:
    result = urlparse.urlparse(url)
    if (result.scheme == 'sop' and re.match('/\d+\Z', result.path)):
        if xbmc.getCondVisibility('system.platform.android'):
            OS_VERSION = xbmc.getInfoLabel("System.OSVersionInfo")
            API_LEVEL = int(re.search('API level (\d+)', OS_VERSION).group(1))
            if API_LEVEL < 20:
                try:
                    #android <5.0 sopclient
                    ENGINE = get_android_old_sopcast()
                    test_exe(ENGINE,ENV)
                except:
                    #fallback
                    APKS = ["org.sopcast.android", "com.trimarts.soptohttp"]
                    for EXTERNAL_SOP in APKS:
                        if os.path.exists(os.path.join("/data", "data", EXTERNAL_SOP)):
                            SOP_ACTIVITY = """XBMC.StartAndroidActivity("{0}","android.intent.action.VIEW","",{1})""".format(EXTERNAL_SOP, url)
                            break
                    xbmc.executebuiltin(SOP_ACTIVITY)
            else:
                APKS = ["org.sopcast.android", "com.devaward.soptohttp"]
                for EXTERNAL_SOP in APKS:
                    if os.path.exists(os.path.join("/data", "data", EXTERNAL_SOP)):
                        SOP_ACTIVITY = """XBMC.StartAndroidActivity("{0}","android.intent.action.VIEW","",{1})""".format(EXTERNAL_SOP, url)
                        break
                xbmc.executebuiltin(SOP_ACTIVITY)
        elif xbmc.getCondVisibility('system.platform.linux'):
            cpu = platform.machine()
            if 'x86' in cpu:
                if os.path.exists('/usr/bin/sp-sc-auth'):
                    #system installed engine
                    ENGINE = ['/usr/bin/sp-sc-auth']
                    test_exe(ENGINE,ENV)
                else:
                    #bundeled engine
                    is_exe(LINUX_X86_SOPCLIENT)
                    env = os.environ.copy()
                    env["LD_LIBRARY_PATH"] = LINUX_X86
                    ENV = env
                    ENGINE = LINUX_X86_SOPCLIENT
                    test_exe(ENGINE,ENV)

            elif 'arm' in cpu:
                is_exe(LINUX_ARM_QEMU_SOPCLIENT)
                is_exe(LINUX_ARM_LD)
                ENGINE = [LINUX_ARM_QEMU_SOPCLIENT, LINUX_ARM_LD, "--library-path", os.path.join(LINUX_ARM, "lib"), LINUX_ARM_SOPCLIENT]
                test_exe(ENGINE,ENV)
            elif 'aar' in cpu:
                is_exe(LINUX_A64_QEMU_SOPCLIENT)
                is_exe(LINUX_ARM_LD)
                ENGINE = [LINUX_A64_QEMU_SOPCLIENT, LINUX_ARM_LD, "--library-path", os.path.join(LINUX_ARM, "lib"), LINUX_ARM_SOPCLIENT]
                test_exe(ENGINE,ENV)
            else:
                #no engine
                pass
        elif xbmc.getCondVisibility('system.platform.windows'):
            DOCKER = 'danihodovic/sopcast'

        if ENGINE:
            # kill busy dialog
            if addon_handle > -1:
                xbmcplugin.endOfDirectory(addon_handle, False, False, False)
            sopclient.SopCastPlayer(engine=ENGINE, env=ENV).playChannel(url, timeout)
        elif DOCKER:
            # kill busy dialog
            if addon_handle > -1:
                xbmcplugin.endOfDirectory(addon_handle, False, False, False)
            dockersopcast.DockerSopCastPlayer(container=DOCKER).playChannel(url, timeout)
        elif not SOP_ACTIVITY:
            #external player
            li = ListItem(path=url)
            xbmcplugin.setResolvedUrl(addon_handle, True, li)


