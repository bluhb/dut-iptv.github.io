from resources.lib.base.l1.constants import ADDON
from resources.lib.base.l2.log import log

try:
    unicode
except NameError:
    unicode = str

def format_string(string, _bold=False, _label=False, _color=None, _strip=False, **kwargs):
    if kwargs:
        string = string.format(**kwargs)

    if _strip:
        string = string.strip()

    if _label:
        _bold = True
        string = u'~ {} ~'.format(string)

    if _bold:
        string = u'[B]{}[/B]'.format(string)

    if _color:
        string = u'[COLOR {}]{}[/COLOR]'.format(_color, string)

    return string

def addon_string(id):
    string = ADDON.getLocalizedString(id)

    if not string:
        log("LANGUAGE: Addon didn't return a string for id: {}".format(id))
        string = unicode(id)

    return string

class BaseLanguage(object):
    ASK_USERNAME = 30001
    ASK_PASSWORD = 30002
    SET_IPTV = 30003
    SET_KODI = 30005
    LIVE_TV = 30007
    SERIES = 30010
    MOVIES = 30011
    NEXT_PAGE = 30021
    CHANNELS = 30024
    HBO_SERIES = 30025
    HBO_MOVIES = 30026
    KIDS_SERIES = 30027
    SHOWMOVIESSERIES = 30028
    KIDS_MOVIES = 30029
    SEASON = 30031
    LOGIN_ERROR_TITLE = 30033
    LOGIN_ERROR = 30034
    EMPTY_USER = 30035
    EMPTY_PASS = 30036

    PLUGIN_LOGIN_REQUIRED = 32000
    PLUGIN_NO_DEFAULT_ROUTE = 32001
    PLUGIN_RESET_YES_NO = 32002
    PLUGIN_RESET_OK = 32003
    ROUTER_NO_FUNCTION = 32006
    ROUTER_NO_URL = 32007
    IA_NOT_FOUND = 32008
    IA_UWP_ERROR = 32009
    IA_KODI18_REQUIRED = 32010
    IA_AARCH64_ERROR = 32011
    IA_NOT_SUPPORTED = 32012
    IA_DOWNLOADING_FILE = 32014
    IA_WIDEVINE_DRM = 32015
    RESET = 32019
    PLUGIN_ERROR = 32020
    INSTALL_WV_DRM = 32021
    IA_WV_INSTALL_OK = 32022
    LOGIN = 32024
    LOGOUT = 32025
    SETTINGS = 32026
    LOGOUT_YES_NO = 32027
    SEARCH = 32029
    SEARCH_FOR = 32030
    PLUGIN_EXCEPTION = 32032
    ERROR_DOWNLOADING_FILE = 32033
    NEW_IA_VERSION = 32038
    MD5_MISMATCH = 32040
    NO_ITEMS = 32041
    NO_ERROR_MSG = 32052
    CHECKED_ENTITLEMENTS = 32053
    PLAY_ERROR = 32054
    NO_STREAM_AUTH = 32055
    NO_REPLAY_TV_INFO = 32056
    DISABLE_ONLY_STANDARD = 32057
    STREAM_NOT_FOUND = 32058
    STREAM_NOT_AVAILABLE = 32059
    NO_MOVIES_SERIES = 32060
    YES_MOVIES_SERIES = 32061
    DONE_REBOOT = 32063
    PROGSAZ = 32064
    PROGSAZDESC = 32065
    OTHERTITLES = 32066
    TITLESWITH = 32067
    OTHERTITLESDESC = 32068
    TITLESWITHDESC = 32069
    CHECK_ENTITLEMENTS = 32070
    DONE_NOREBOOT = 32071
    DOWNLOAD_EPG = 32072
    DOWNLOAD_SETTINGS = 32073
    SEARCHMENU = 32074
    NEWSEARCH = 32075
    NEWSEARCHDESC = 32076
    TODAY = 32079
    YESTERDAY = 32080
    ENABLE_SIMPLE_IPTV = 32081
    RESET_SESSION = 32082
    ADD_TO_WATCHLIST = 32083
    REMOVE_FROM_WATCHLIST = 32084
    WATCHLIST = 32085
    ADDED_TO_WATCHLIST = 32086
    ADD_TO_WATCHLIST_FAILED = 32087
    REMOVED_FROM_WATCHLIST = 32088
    REMOVE_FROM_WATCHLIST_FAILED = 32089
    START_FROM_BEGINNING = 32093
    TOO_MANY_DEVICES = 32094
    WATCHAHEAD = 32095
    RECOMMENDED = 32096
    SERIESBINGE = 32097
    MOSTVIEWED = 32098
    LOGIN_ERROR2 = 32100
    CHANNEL_PICKER = 320104
    TEST_SUCCESS = 320105
    TEST_FAILED = 320106
    NOT_TESTED = 320107
    AUTO_CHOICE = 320108
    MANUAL_CHOICE = 320109
    SIMPLEIPTV = 320110
    AUTO_CHOICE_SET = 320112
    TEST_CHANNEL = 320113
    START_BEGINNING = 320114
    LOGIN_SUCCESS = 320115
    PROXY_NOT_SET = 320116
    ASK_USERNAME2 = 320117
    ASK_PASSWORD2 = 320118
    EMPTY_USER2 = 320119
    EMPTY_PASS2 = 320120
    VIDEOSHOP = 320121

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if not isinstance(attr, int):
            return attr

        return addon_string(attr)

    def __call__(self, string, **kwargs):
        if isinstance(string, int):
            string = addon_string(string)

        return format_string(string, **kwargs)

_ = BaseLanguage()