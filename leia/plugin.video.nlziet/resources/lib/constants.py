from resources.lib.base.language import _

CONST_API_URL = 'https://api.nlziet.nl'

CONST_BASE_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
    'Cache-Control': 'no-cache',
    'DNT': '1',
    'Origin': 'https://app.nlziet.nl',
    'Pragma': 'no-cache',
    'Referer': 'https://app.nlziet.nl/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

CONST_BASE_URL = 'https://www.nlziet.nl'
CONST_IMAGE_URL = 'https://nlzietprodstorage.blob.core.windows.net'

CONST_ONLINE_SEARCH = True

CONST_VOD_CAPABILITY = [
    { 'file': 'series', 'label': _.SERIES, 'start': 0, 'online': 0, 'split': 1 },
    { 'file': 'tipfeed', 'label': _.RECOMMENDED, 'start': 0, 'online': 1, 'split': 0 },
    { 'file': 'watchahead', 'label': _.WATCHAHEAD, 'start': 0, 'online': 1, 'split': 0 },
    { 'file': 'movies', 'label': _.MOVIES, 'start': 0, 'online': 1, 'split': 0 },
    { 'file': 'seriesbinge', 'label': _.SERIESBINGE, 'start': 0, 'online': 1, 'split': 0 },
    { 'file': 'mostviewed', 'label': _.MOSTVIEWED, 'start': 0, 'online': 1, 'split': 0 },
]

CONST_WATCHLIST = False

SETUP_DB_QUERIES = [
    '''CREATE TABLE IF NOT EXISTS `vars` (
        `profile_id` INT(11) PRIMARY KEY,
        `arch` VARCHAR(255) DEFAULT '',
        `cookies` TEXT DEFAULT '',
        `epg_md5` VARCHAR(255) DEFAULT '',
        `epgrun` TINYINT(1) DEFAULT 0,
        `epgruntime` INT(11) DEFAULT 0,
        `first_boot` TINYINT(1) DEFAULT 1,
        `images_md5` VARCHAR(255) DEFAULT '',
        `img_size` VARCHAR(255) DEFAULT '',
        `last_login_success` TINYINT(1) DEFAULT 0,
        `last_login_time` INT(11) DEFAULT 0,
        `last_playing` INT(11) DEFAULT 0,
        `last_tested` VARCHAR(255) DEFAULT '',
        `proxyserver_port` INT(11) DEFAULT 0,
        `pswd` VARCHAR(255) DEFAULT '',
        `resource_key` VARCHAR(255) DEFAULT '',
        `resource_secret` VARCHAR(255) DEFAULT '',
        `resource_verifier` VARCHAR(255) DEFAULT '',
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
        `stream_duration` INT(11) DEFAULT 0,
        `stream_hostname` VARCHAR(255) DEFAULT '',
        `system` VARCHAR(255) DEFAULT '',
        `test_running` TINYINT(1) DEFAULT 0,
        `user_agent` VARCHAR(255) DEFAULT '',
        `username` VARCHAR(255) DEFAULT '',
        `vod_md5` VARCHAR(255) DEFAULT ''
    )''',
]