import __builtin__
import os

setattr(__builtin__, 'addon_id', os.path.basename(os.path.abspath(os.path.dirname(__file__))))

import xbmcgui
from ottclub import Ottclub
from iptvlib import *
from iptvlib.mainwindow import MainWindow


class Main(object):
    def __init__(self):
        self.main_window = MainWindow.create(self.check_settings)
        self.main_window.doModal()
        del self.main_window

    def check_settings(self):
        # type: () -> bool
        playlist = addon.getSetting("playlist")
        key = addon.getSetting("key")
        if playlist == "" or key == "":

            dialog = xbmcgui.Dialog()
            yesno = bool(
                dialog.yesno(
                    addon.getAddonInfo("name"), " ",
                    get_string(TEXT_SUBSCRIPTION_REQUIRED_ID),
                    get_string(TEXT_SET_CREDENTIALS_ID)
                )
            )
            del dialog
            if yesno is True:
                addon.openSettings()
                return self.check_settings()
            else:
                return False

        adult = addon.getSetting("adult") == 'true' or \
                           addon.getSetting("adult") == True

        self.main_window.api = Ottclub(
            playlist,
            key,
            adult,
            working_path=xbmc.translatePath(addon.getAddonInfo("profile"))
        )

        return True


if __name__ == "__main__":
    Main()
