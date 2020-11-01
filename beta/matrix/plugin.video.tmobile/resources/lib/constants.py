from resources.lib.base.l3.language import _

CONST_BASE_URL = 'https://t-mobiletv.nl'

CONST_BASE_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'nl',
    'Cache-Control': 'no-cache',
    'DNT': '1',
    'Origin': CONST_BASE_URL,
    'Pragma': 'no-cache',
    'Referer': CONST_BASE_URL + '/inloggen/index.html',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

CONST_ONLINE_SEARCH = False

CONST_VOD_CAPABILITY = [
    { 'file': 'series', 'label': _.SERIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'film1', 'label': _.MOVIES, 'start': 0, 'online': 0, 'split': 0 },
    { 'file': 'videoshop', 'label': _.VIDEOSHOP, 'start': 0, 'online': 0, 'split': 0 },
]

CONST_WATCHLIST = False

SETUP_DB_QUERIES = [
    '''CREATE TABLE IF NOT EXISTS `vars` (
        `profile_id` INT(11) PRIMARY KEY,
        `arch` VARCHAR(255) DEFAULT '',
        `channels_age` INT(11) DEFAULT 0,
        `cookies` TEXT DEFAULT '',
        `csrf_token` VARCHAR(255) DEFAULT '',
        `devicekey` VARCHAR(255) DEFAULT '',
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
        `search1` VARCHAR(255) DEFAULT '',
        `search2` VARCHAR(255) DEFAULT '',
        `search3` VARCHAR(255) DEFAULT '',
        `search4` VARCHAR(255) DEFAULT '',
        `search5` VARCHAR(255) DEFAULT '',
        `search6` VARCHAR(255) DEFAULT '',
        `search7` VARCHAR(255) DEFAULT '',
        `search8` VARCHAR(255) DEFAULT '',
        `search9` VARCHAR(255) DEFAULT '',
        `search10` VARCHAR(255) DEFAULT '',
        `stream_duration` INT(11) DEFAULT 0,
        `stream_hostname` VARCHAR(255) DEFAULT '',
        `system` VARCHAR(255) DEFAULT '',
        `test_running` TINYINT(1) DEFAULT 0,
        `user_agent` VARCHAR(255) DEFAULT '',
        `user_filter` VARCHAR(255) DEFAULT '',
        `username` VARCHAR(255) DEFAULT '',
        `vod_md5` VARCHAR(255) DEFAULT ''
    )''',
]