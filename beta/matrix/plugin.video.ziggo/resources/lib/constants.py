from resources.lib.base.l3.language import _

CONST_ALLOWED_HEADERS = {
    'user-agent',
    'x-oesp-content-locator',
    'x-oesp-token',
    'x-client-id',
    'x-oesp-username',
    'x-oesp-drm-schemeiduri'
}

CONST_BASE_URL = 'https://www.ziggogo.tv'

CONST_BASE_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
    'Cache-Control': 'no-cache',
    'DNT': '1',
    'Origin': CONST_BASE_URL,
    'Pragma': 'no-cache',
    'Referer': CONST_BASE_URL + '/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
}

CONST_DEFAULT_CLIENTID = '4.23.13'

CONST_ONLINE_SEARCH = True

CONST_VOD_CAPABILITY = [
    { 'file': 'series', 'label': _.SERIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'movies', 'label': _.MOVIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'hboseries', 'label': _.HBO_SERIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'hbomovies', 'label': _.HBO_MOVIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'kidsseries', 'label': _.KIDS_SERIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'kidsmovies', 'label': _.KIDS_MOVIES, 'start': 0, 'online': 0, 'split': 0 },
]

CONST_WATCHLIST = False

SETUP_DB_QUERIES = [
    '''CREATE TABLE IF NOT EXISTS `vars` (
        `profile_id` INT(11) PRIMARY KEY,
        `access_token` TEXT DEFAULT '',
        `arch` VARCHAR(255) DEFAULT '',
        `base_url` VARCHAR(255) DEFAULT '',
        `base_v3` TINYINT(1) DEFAULT 0,
        `channels_url` VARCHAR(255) DEFAULT '',
        `client_id` VARCHAR(255) DEFAULT '',
        `cookies` TEXT DEFAULT '',
        `devices_url` VARCHAR(255) DEFAULT '',
        `drm_token` VARCHAR(255) DEFAULT '',
        `drm_token_age` INT(11) DEFAULT 0,
        `drm_locator` VARCHAR(255) DEFAULT '',
        `epg_md5` VARCHAR(255) DEFAULT '',
        `epgrun` TINYINT(1) DEFAULT 0,
        `epgruntime` INT(11) DEFAULT 0,
        `first_boot` TINYINT(1) DEFAULT 1,
        `household_id` VARCHAR(255) DEFAULT '',
        `images_md5` VARCHAR(255) DEFAULT '',
        `img_size` VARCHAR(255) DEFAULT '',
        `last_login_success` TINYINT(1) DEFAULT 0,
        `last_login_time` INT(11) DEFAULT 0,
        `last_playing` INT(11) DEFAULT 0,
        `last_tested` VARCHAR(255) DEFAULT '',
        `listings_url` VARCHAR(255) DEFAULT '',
        `mediagroupsfeeds_url` VARCHAR(255) DEFAULT '',
        `mediaitems_url` VARCHAR(255) DEFAULT '',
        `ziggo_profile_id` VARCHAR(255) DEFAULT '',
        `proxyserver_port` INT(11) DEFAULT 0,
        `pswd` VARCHAR(255) DEFAULT '',
        `search1` VARCHAR(255) DEFAULT '',
        `search_type1` TINYINT(1) DEFAULT 0,
        `search2` VARCHAR(255) DEFAULT '',
        `search_type2` TINYINT(1) DEFAULT 0,
        `search3` VARCHAR(255) DEFAULT '',
        `search_type3` TINYINT(1) DEFAULT 0,
        `search4` VARCHAR(255) DEFAULT '',
        `search_type4` TINYINT(1) DEFAULT 0,
        `search5` VARCHAR(255) DEFAULT '',
        `search_type5` TINYINT(1) DEFAULT 0,
        `search6` VARCHAR(255) DEFAULT '',
        `search_type6` TINYINT(1) DEFAULT 0,
        `search7` VARCHAR(255) DEFAULT '',
        `search_type7` TINYINT(1) DEFAULT 0,
        `search8` VARCHAR(255) DEFAULT '',
        `search_type8` TINYINT(1) DEFAULT 0,
        `search9` VARCHAR(255) DEFAULT '',
        `search_type9` TINYINT(1) DEFAULT 0,
        `search10` VARCHAR(255) DEFAULT '',
        `search_type10` TINYINT(1) DEFAULT 0,
        `search_url` VARCHAR(255) DEFAULT '',
        `session_url` VARCHAR(255) DEFAULT '',
        `stream_duration` INT(11) DEFAULT 0,
        `stream_hostname` VARCHAR(255) DEFAULT '',
        `system` VARCHAR(255) DEFAULT '',
        `test_running` TINYINT(1) DEFAULT 0,
        `tokenrun` TINYINT(1) DEFAULT 0,
        `tokenruntime` INT(11) DEFAULT 0,
        `token_url` INT(11) DEFAULT 0,
        `user_agent` VARCHAR(255) DEFAULT '',
        `username` VARCHAR(255) DEFAULT '',
        `vod_md5` VARCHAR(255) DEFAULT '',
        `watchlist_id` VARCHAR(255) DEFAULT '',
        `watchlist_url` VARCHAR(255) DEFAULT '',
        `widevine_url` VARCHAR(255) DEFAULT ''
    )''',
]