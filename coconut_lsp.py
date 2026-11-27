"""Sublime Text: register the bundled Coconut language server with the LSP package.

If the LSP package (https://packagecontrol.io/packages/LSP) is installed, this makes the
Coconut language server (server/coconut_language_server.py) start automatically for Coconut
files. Configure it with Preferences > Package Settings > Coconut > LSP Settings, e.g. to point
"command" at the Python interpreter that has Coconut installed. Without LSP, this does nothing.
"""

import os

import sublime

try:
    from LSP.plugin import AbstractPlugin, register_plugin, unregister_plugin
except ImportError:
    AbstractPlugin = None

PACKAGE_NAME = __package__ or "Coconut"
SETTINGS_FILE = "LSP-coconut.sublime-settings"


def server_path():
    return os.path.join(sublime.packages_path(), PACKAGE_NAME, "server", "coconut_language_server.py")


if AbstractPlugin is not None:

    class Coconut(AbstractPlugin):

        @classmethod
        def name(cls):
            return "coconut"

        @classmethod
        def configuration(cls):
            return sublime.load_settings(SETTINGS_FILE), "Packages/{p}/{f}".format(p=PACKAGE_NAME, f=SETTINGS_FILE)

        @classmethod
        def additional_variables(cls):
            return {
                "server_path": server_path(),
                "python": "python" if sublime.platform() == "windows" else "python3",
            }

    def plugin_loaded():
        if not os.path.isfile(server_path()):
            print("Coconut: language server not found at {p} (is the package installed as a folder?)".format(p=server_path()))
            return
        register_plugin(Coconut)

    def plugin_unloaded():
        unregister_plugin(Coconut)
