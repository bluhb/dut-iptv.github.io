import json, os, random, re, string, time, xbmc

from resources.lib.base import gui, settings
from resources.lib.base.api import api_download
from resources.lib.base.constants import ADDON_ID, ADDON_PROFILE
from resources.lib.base.exceptions import Error
from resources.lib.base.language import _
from resources.lib.base.log import log
from resources.lib.base.session import Session
from resources.lib.base.util import check_key, clean_filename, combine_playlist, find_highest_bandwidth, get_credentials, is_file_older_than_x_minutes, load_file, load_profile, load_tests, query_epg, query_settings, set_credentials, update_prefs, write_file
from resources.lib.constants import CONST_BASE_HEADERS, CONST_BASE_URL

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

try:
    unicode
except NameError:
    unicode = str

try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite

class APIError(Error):
    pass

class API(object):
    def login(self):
        creds = get_credentials()
        username = creds['username']
        password = creds['password']

        query = "UPDATE `vars` SET `csrf_token`='', `cookies`='', `user_filter`='' WHERE profile_id={profile_id}".format(profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        profile_settings = load_profile(profile_id=1)

        if len(profile_settings['devicekey']) == 0:
            devicekey = ''.join(random.choice(string.digits) for _ in range(10))
            query = "UPDATE `vars` SET `devicekey`='{devicekey}' WHERE profile_id={profile_id}".format(devicekey=devicekey, profile_id=1)
            query_settings(query=query, return_result=False, return_insert=False, commit=True)

        login_url = '{base_url}/VSP/V3/Authenticate?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

        session_post_data = {
            "authenticateBasic": {
                'VUID': '6_7_{devicekey}'.format(devicekey=profile_settings['devicekey']),
                'clientPasswd': password,
                'isSupportWebpImgFormat': '0',
                'lang': 'nl',
                'needPosterTypes': [
                    '1',
                    '2',
                    '3',
                    '4',
                    '5',
                    '6',
                    '7',
                ],
                'timeZone': 'Europe/Amsterdam',
                'userID': username,
                'userType': '0',
            },
            'authenticateDevice': {
                'CADeviceInfos': [
                    {
                        'CADeviceID': profile_settings['devicekey'],
                        'CADeviceType': '7',
                    },
                ],
                'deviceModel': '3103_PCClient',
                'physicalDeviceID': profile_settings['devicekey'],
                'terminalID': profile_settings['devicekey'],
            },
            'authenticateTolerant': {
                'areaCode': '',
                'bossID': '',
                'subnetID': '',
                'templateName': '',
                'userGroup': '',
            },
        }

        download = api_download(url=login_url, type='post', headers=None, data=session_post_data, json_data=True, return_json=True)
        data = download['data']
        code = download['code']

        if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'csrfToken'):
            if check_key(data, 'result') and check_key(data['result'], 'retCode') and data['result']['retCode'] == "157022007" and check_key(data, 'devices'):
                for row in data['devices']:
                    if not check_key(row, 'name') and check_key(row, 'deviceModel') and check_key(row, 'status') and check_key(row, 'onlineState') and check_key(row, 'physicalDeviceID') and row['deviceModel'] == '3103_PCClient' and row['status'] == '1' and row['onlineState'] == '0':
                        query = "UPDATE `vars` SET `devicekey`='{devicekey}' WHERE profile_id={profile_id}".format(devicekey=row['physicalDeviceID'], profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return self.login()

            return { 'code': code, 'data': data, 'result': False }

        query = "UPDATE `vars` SET `csrf_token`='{csrf_token}', `user_filter`='{user_filter}' WHERE profile_id={profile_id}".format(csrf_token=data['csrfToken'], user_filter=data['userFilter'], profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        return { 'code': code, 'data': data, 'result': True }

    def get_session(self):
        profile_settings = load_profile(profile_id=1)

        if check_key(profile_settings, 'last_login_time') and profile_settings['last_login_time'] > int(time.time() - 3600) and profile_settings['last_login_success'] == 1:
            return True

        heartbeat_url = '{base_url}/VSP/V3/OnLineHeartbeat?from=inMSAAccess'.format(base_url=CONST_BASE_URL)

        headers = {'Content-Type': 'application/json', 'X_CSRFToken': profile_settings['csrf_token']}

        session_post_data = {}

        download = api_download(url=heartbeat_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
        data = download['data']
        code = download['code']

        if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000':
            login_result = self.login()

            if not login_result['result']:
                return False

        try:
            query = "UPDATE `vars` SET `last_login_time`={last_login_time}, `last_login_success`=1 WHERE profile_id={profile_id}".format(last_login_time=int(time.time()),profile_id=1)
            query_settings(query=query, return_result=False, return_insert=False, commit=True)
        except:
            pass

        return True

    def test_channels(self, tested=False, channel=None):
        profile_settings = load_profile(profile_id=1)

        if channel:
            channel = unicode(channel)

        try:
            if not profile_settings['last_login_success'] == 1 or not settings.getBool(key='run_tests') or not self.get_session():
                return 5

            query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=1,profile_id=1)
            query_settings(query=query, return_result=False, return_insert=False, commit=True)

            query = "SELECT * FROM `channels`"
            channels = query_epg(query=query, return_result=True, return_insert=False, commit=False)
            results = load_tests(profile_id=1)

            count = 0
            first = True
            last_tested_found = False
            test_run = False
            user_agent = profile_settings['user_agent']

            if not results:
                results = {}

            for row in channels:
                if count == 5 or (count == 1 and tested):
                    if test_run:
                        update_prefs()

                    query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                    query_settings(query=query, return_result=False, return_insert=False, commit=True)
                    return count

                id = unicode(row['id'])

                if len(id) > 0:
                    if channel:
                        if not id == channel:
                            continue
                    elif tested:
                        if unicode(profile_settings['last_tested']) == id:
                            last_tested_found = True
                            continue
                        elif last_tested_found:
                            pass
                        else:
                            continue

                    if check_key(results, id) and not tested and not first:
                        continue

                    livebandwidth = 0
                    replaybandwidth = 0
                    live = 0
                    replay = 0
                    epg = 0
                    guide = 0

                    profile_settings = load_profile(profile_id=1)

                    if profile_settings['last_playing'] > int(time.time() - 300):
                        if test_run:
                            update_prefs()

                        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return 5

                    playdata = self.play_url(type='channel', channel=id, id=None, test=True)

                    if first and not profile_settings['last_login_success']:
                        if test_run:
                            update_prefs()

                        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return 5

                    if len(playdata['path']) > 0:
                        CDMHEADERS = {
                            'User-Agent': user_agent,
                            'X_CSRFToken': profile_settings['csrf_token'],
                            'Cookie': playdata['license']['cookie'],
                        }

                        if check_key(playdata, 'license') and check_key(playdata['license'], 'triggers') and check_key(playdata['license']['triggers'][0], 'licenseURL'):
                            if check_key(playdata['license']['triggers'][0], 'customData'):
                                CDMHEADERS['AcquireLicense.CustomData'] = playdata['license']['triggers'][0]['customData']
                                CDMHEADERS['CADeviceType'] = 'Widevine OTT client'

                        session = Session(headers=CDMHEADERS)
                        resp = session.get(playdata['path'])

                        if resp.status_code == 200:
                            livebandwidth = find_highest_bandwidth(xml=resp.text)
                            live = 1

                    if check_key(results, id) and first and not tested:
                        first = False

                        if live == 1:
                            continue
                        else:
                            if test_run:
                                update_prefs()

                            query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                            query_settings(query=query, return_result=False, return_insert=False, commit=True)
                            return 5

                    first = False
                    counter = 0

                    while not self._abortRequested and not xbmc.Monitor().abortRequested() and counter < 5:
                        if self._abortRequested or xbmc.Monitor().waitForAbort(1):
                            self._abortRequested = True
                            break

                        counter += 1

                        profile_settings = load_profile(profile_id=1)

                        if profile_settings['last_playing'] > int(time.time() - 300):
                            if test_run:
                                update_prefs()

                            query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                            query_settings(query=query, return_result=False, return_insert=False, commit=True)
                            return 5

                    if self._abortRequested or xbmc.Monitor().abortRequested():
                        return 5

                    militime = int(int(time.time() - 86400) * 1000)

                    session_post_data = {
                        'needChannel': '0',
                        'queryChannel': {
                            'channelIDs': [
                                id,
                            ],
                            'isReturnAllMedia': '1',
                        },
                        'queryPlaybill': {
                            'count': '1',
                            'endTime': militime,
                            'isFillProgram': '1',
                            'offset': '0',
                            'startTime': militime,
                            'type': '0',
                        }
                    }

                    headers = {'Content-Type': 'application/json', 'X_CSRFToken': profile_settings['csrf_token']}

                    channel_url = '{base_url}/VSP/V3/QueryPlaybillListStcProps?SID=queryPlaybillListStcProps3&DEVICE=PC&DID={deviceID}&from=throughMSAAccess'.format(base_url=CONST_BASE_URL, deviceID=profile_settings['devicekey'])

                    download = api_download(url=channel_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
                    data = download['data']
                    code = download['code']

                    if code and code == 200 and data and check_key(data, 'channelPlaybills') and check_key(data['channelPlaybills'][0], 'playbillLites') and check_key(data['channelPlaybills'][0]['playbillLites'][0], 'ID'):
                        profile_settings = load_profile(profile_id=1)

                        if profile_settings['last_playing'] > int(time.time() - 300):
                            if test_run:
                                update_prefs()

                            query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                            query_settings(query=query, return_result=False, return_insert=False, commit=True)
                            return 5

                        playdata = self.play_url(type='program', channel=id, id=data['channelPlaybills'][0]['playbillLites'][0]['ID'], test=True)

                        if len(playdata['path']) > 0:
                            CDMHEADERS = {
                                'User-Agent': user_agent,
                                'X_CSRFToken': profile_settings['csrf_token'],
                                'Cookie': playdata['license']['cookie'],
                            }

                            if check_key(playdata, 'license') and check_key(playdata['license'], 'triggers') and check_key(playdata['license']['triggers'][0], 'licenseURL'):
                                if check_key(playdata['license']['triggers'][0], 'customData'):
                                    CDMHEADERS['AcquireLicense.CustomData'] = playdata['license']['triggers'][0]['customData']
                                    CDMHEADERS['CADeviceType'] = 'Widevine OTT client'

                            session = Session(headers=CDMHEADERS)
                            resp = session.get(playdata['path'])

                            if resp.status_code == 200:
                                replaybandwidth = find_highest_bandwidth(xml=resp.text)
                                replay = 1

                    query = "SELECT id FROM `epg` WHERE channel='{channel}' LIMIT 1".format(channel=id)
                    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

                    if len(data) > 0:
                        guide = 1

                        if live == 1:
                            epg = 1

                    if not self._abortRequested:
                        query = "UPDATE `vars` SET `last_tested`='{last_tested}' WHERE profile_id={profile_id}".format(last_tested=id,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)

                        query = "REPLACE INTO `tests_{profile_id}` VALUES ('{id}', '{live}', '{livebandwidth}', '{replay}', '{replaybandwidth}', '{epg}', '{guide}')".format(profile_id=1, id=id, live=live, livebandwidth=livebandwidth, replay=replay, replaybandwidth=replaybandwidth, epg=epg, guide=guide)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)

                    test_run = True
                    counter = 0

                    while not self._abortRequested and not xbmc.Monitor().abortRequested() and counter < 15:
                        if self._abortRequested or xbmc.Monitor().waitForAbort(1):
                            self._abortRequested = True
                            break

                        counter += 1

                        profile_settings = load_profile(profile_id=1)

                        if profile_settings['last_playing'] > int(time.time() - 300):
                            if test_run:
                                update_prefs()

                            query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                            query_settings(query=query, return_result=False, return_insert=False, commit=True)
                            return 5

                    if self._abortRequested or xbmc.Monitor().abortRequested():
                        return 5

                    count += 1
        except:
            if test_run:
                update_prefs()

            count = 5

        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        return count

    def play_url(self, type, channel=None, id=None, video_data=None, test=False, from_beginning=0):
        playdata = {'path': '', 'license': '', 'info': ''}

        if not self.get_session():
            return playdata

        from_beginning = int(from_beginning)
        profile_settings = load_profile(profile_id=1)

        headers = {'Content-Type': 'application/json', 'X_CSRFToken': profile_settings['csrf_token']}

        mediaID = None
        info = {}

        if not type or not len(unicode(type)) > 0:
            return playdata

        if not test:
            counter = 0

            while not self._abortRequested and not xbmc.Monitor().abortRequested() and counter < 5:
                profile_settings = load_profile(profile_id=1)

                if profile_settings['test_running'] == 0:
                    break

                counter += 1

                query = "UPDATE `vars` SET `last_playing`={last_playing} WHERE profile_id={profile_id}".format(last_playing=int(time.time()),profile_id=1)
                query_settings(query=query, return_result=False, return_insert=False, commit=True)

                if self._abortRequested or xbmc.Monitor().waitForAbort(1):
                    self._abortRequested = True
                    break

            if self._abortRequested or xbmc.Monitor().abortRequested():
                return playdata

        militime = int(time.time() * 1000)

        if not type == 'vod':
            if video_data:
                try:
                    video_data = json.loads(video_data)
                    mediaID = int(video_data['media_id']) + 1
                except:
                    pass

            query = "SELECT assetid FROM `channels` WHERE id='{channel}'".format(channel=channel)
            data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

            if data:
                for row in data:
                    mediaID = row['assetid']

        if type == 'channel' and channel:
            if not test:
                session_post_data = {
                    'needChannel': '0',
                    'queryChannel': {
                        'channelIDs': [
                            channel,
                        ],
                        'isReturnAllMedia': '1',
                    },
                    'queryPlaybill': {
                        'count': '1',
                        'endTime': militime,
                        'isFillProgram': '1',
                        'offset': '0',
                        'startTime': militime,
                        'type': '0',
                    }
                }

                channel_url = '{base_url}/VSP/V3/QueryPlaybillListStcProps?SID=queryPlaybillListStcProps3&DEVICE=PC&DID={deviceID}&from=throughMSAAccess'.format(base_url=CONST_BASE_URL, deviceID=profile_settings['devicekey'])

                download = api_download(url=channel_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
                data = download['data']
                code = download['code']

                if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'channelPlaybills') or not check_key(data['channelPlaybills'][0], 'playbillLites') or not check_key(data['channelPlaybills'][0]['playbillLites'][0], 'ID'):
                    return playdata

                id = data['channelPlaybills'][0]['playbillLites'][0]['ID']

                session_post_data = {
                    'playbillID': id,
                    'channelNamespace': '310303',
                    'isReturnAllMedia': '1',
                }

                program_url = '{base_url}/VSP/V3/QueryPlaybill?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

                download = api_download(url=program_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
                data = download['data']
                code = download['code']

                if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'playbillDetail'):
                    info = {}
                else:
                    info = data['playbillDetail']

            session_post_data = {
                "businessType": "BTV",
                "channelID": channel,
                "checkLock": {
                    "checkType": "0",
                },
                "isHTTPS": "1",
                "isReturnProduct": "1",
                "mediaID": mediaID,
            }

        elif type == 'program' and id:
            if not test:
                session_post_data = {
                    'playbillID': id,
                    'channelNamespace': '310303',
                    'isReturnAllMedia': '1',
                }

                program_url = '{base_url}/VSP/V3/QueryPlaybill?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

                download = api_download(url=program_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
                data = download['data']
                code = download['code']

                if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'playbillDetail'):
                    info = {}
                else:
                    info = data['playbillDetail']

            session_post_data = {
                "businessType": "CUTV",
                "channelID": channel,
                "checkLock": {
                    "checkType": "0",
                },
                "isHTTPS": "1",
                "isReturnProduct": "1",
                "mediaID": mediaID,
                "playbillID": id,
            }
        elif type == 'vod' and id:
            session_post_data = {
                'VODID': id
            }

            program_url = '{base_url}/VSP/V3/QueryVOD?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

            download = api_download(url=program_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
            data = download['data']
            code = download['code']

            if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'VODDetail') or not check_key(data['VODDetail'], 'VODType'):
                return playdata

            info = data['VODDetail']

            session_post_data = {
                "VODID": id,
                "checkLock": {
                    "checkType": "0",
                },
                "isHTTPS": "1",
                "isReturnProduct": "1",
                "mediaID": '',
            }

            if not check_key(info, 'mediaFiles') or not check_key(info['mediaFiles'][0], 'ID'):
                return playdata

            if check_key(info, 'series') and check_key(info['series'][0], 'VODID'):
                session_post_data["seriesID"] = info['series'][0]['VODID']

            session_post_data["mediaID"] = info['mediaFiles'][0]['ID']

        if not len(unicode(session_post_data["mediaID"])) > 0:
            return playdata

        if type == 'vod':
            play_url_path = '{base_url}/VSP/V3/PlayVOD?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)
        else:
            play_url_path = '{base_url}/VSP/V3/PlayChannel?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

        if self._abortRequested or xbmc.Monitor().abortRequested():
            return playdata

        download = api_download(url=play_url_path, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
        data = download['data']
        code = download['code']

        if not code or not code == 200 or not data or not check_key(data, 'result') or not check_key(data['result'], 'retCode') or not data['result']['retCode'] == '000000000' or not check_key(data, 'playURL'):
            return playdata

        path = data['playURL']

        if check_key(data, 'authorizeResult'):
            profile_settings = load_profile(profile_id=1)

            data['authorizeResult']['cookie'] = self.getCookies(profile_settings['cookies'], '')
            license = data['authorizeResult']

        if not test:
            real_url = "{hostscheme}://{netloc}".format(hostscheme=urlparse(path).scheme, netloc=urlparse(path).netloc)
            proxy_url = "http://127.0.0.1:{proxy_port}".format(proxy_port=profile_settings['proxyserver_port'])

            try:
                test_proxy = api_download(url=proxy_url + "/status", type='get', headers=None, data=None, json_data=False, return_json=False)
                code = test_proxy['code']
            except:
                pass

            if not code or not code == 200:
                gui.ok(message=_.PROXY_NOT_SET)
                return playdata

            path = path.replace(real_url, proxy_url)

            query = "UPDATE `vars` SET `stream_hostname`='{stream_hostname}' WHERE profile_id={profile_id}".format(stream_hostname=real_url, profile_id=1)
            query_settings(query=query, return_result=False, return_insert=False, commit=True)

        playdata = {'path': path, 'license': license, 'info': info}

        return playdata

    def vod_seasons(self, id):
        if not self.get_session():
            return None

        seasons = []

        file = "cache" + os.sep + "vod_seasons_" + unicode(id) + ".json"

        if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
            data = load_file(file=file, isJSON=True)
        else:
            profile_settings = load_profile(profile_id=1)

            headers = {'Content-Type': 'application/json', 'X_CSRFToken': profile_settings['csrf_token']}

            session_post_data = {
                'VODID': unicode(id),
                'offset': '0',
                'count': '50',
            }

            seasons_url = '{base_url}/VSP/V3/QueryEpisodeList?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

            download = api_download(url=seasons_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
            data = download['data']
            code = download['code']

            if code and code == 200 and data and check_key(data, 'result') and check_key(data['result'], 'retCode') and data['result']['retCode'] == '000000000' and check_key(data, 'episodes') and settings.getBool(key='enable_cache'):
                write_file(file=file, data=data, isJSON=True)

        if not data or not check_key(data, 'episodes'):
            return None

        for row in data['episodes']:
            if check_key(row, 'VOD') and check_key(row['VOD'], 'ID') and check_key(row, 'sitcomNO'):
                image = ''

                if check_key(row['VOD'], 'picture') and check_key(row['VOD']['picture'], 'posters'):
                    image = row['VOD']['picture']['posters'][0]

                seasons.append({'id': row['VOD']['ID'], 'seriesNumber': row['sitcomNO'], 'description': '', 'image': image})

        return {'type': 'seasons', 'seasons': seasons}

    def vod_season(self, series, id):
        if not self.get_session():
            return None

        season = []

        file = "cache" + os.sep + "vod_season_" + unicode(id) + ".json"

        if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
            data = load_file(file=file, isJSON=True)
        else:
            profile_settings = load_profile(profile_id=1)

            headers = {'Content-Type': 'application/json', 'X_CSRFToken': profile_settings['csrf_token']}

            session_post_data = {
                'VODID': unicode(id),
                'offset': '0',
                'count': '35',
            }

            seasons_url = '{base_url}/VSP/V3/QueryEpisodeList?from=throughMSAAccess'.format(base_url=CONST_BASE_URL)

            download = api_download(url=seasons_url, type='post', headers=headers, data=session_post_data, json_data=True, return_json=True)
            data = download['data']
            code = download['code']

            if code and code == 200 and data and check_key(data, 'result') and check_key(data['result'], 'retCode') and data['result']['retCode'] == '000000000' and check_key(data, 'episodes') and settings.getBool(key='enable_cache'):
                write_file(file=file, data=data, isJSON=True)

        if not data or not check_key(data, 'episodes'):
            return None

        for row in data['episodes']:
            if check_key(row, 'VOD') and check_key(row['VOD'], 'ID') and check_key(row['VOD'], 'name') and check_key(row, 'sitcomNO'):
                image = ''
                duration = 0

                if not check_key(row['VOD'], 'mediaFiles') or not check_key(row['VOD']['mediaFiles'][0], 'ID'):
                    continue

                if check_key(row['VOD']['mediaFiles'][0], 'elapseTime'):
                    duration = row['VOD']['mediaFiles'][0]['elapseTime']

                if check_key(row['VOD'], 'picture') and check_key(row['VOD']['picture'], 'posters'):
                    image = row['VOD']['picture']['posters'][0]

                label = '{episode} - {title}'.format(episode=row['sitcomNO'], title=row['VOD']['name'])

                season.append({'label': label, 'id': row['VOD']['ID'], 'media_id': row['VOD']['mediaFiles'][0]['ID'], 'duration': duration, 'title': row['VOD']['name'], 'episodeNumber': row['sitcomNO'], 'description': '', 'image': image})

        return season

    def getCookies(self, cookie_jar, domain):
        cookie_dict = json.loads(cookie_jar)
        found = ['%s=%s' % (name, value) for (name, value) in cookie_dict.items()]
        return '; '.join(found)