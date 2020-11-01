import base64, datetime, hmac, os, random, re, string, time, xbmc
from hashlib import sha1
from requests_oauthlib import OAuth1

from resources.lib.base.l1.constants import ADDON_ID, ADDON_PROFILE
from resources.lib.base.l2 import settings
from resources.lib.base.l2.log import log
from resources.lib.base.l3.language import _
from resources.lib.base.l3.util import check_key, clean_filename, convert_datetime_timezone, combine_playlist, date_to_nl_dag, date_to_nl_maand, find_highest_bandwidth, get_credentials, is_file_older_than_x_minutes, load_file, load_profile, load_tests, query_epg, query_settings, set_credentials, update_prefs, write_file
from resources.lib.base.l4 import gui
from resources.lib.base.l4.exceptions import Error
from resources.lib.base.l4.session import Session
from resources.lib.base.l5.api import api_download
from resources.lib.constants import CONST_API_URL, CONST_BASE_URL, CONST_IMAGE_URL

try:
    from urllib.parse import parse_qs, urlparse, quote
except ImportError:
    from urlparse import parse_qs, urlparse
    from urllib import quote

try:
    unicode
except NameError:
    unicode = str

try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite

def api_add_to_watchlist():
    return None

def api_get_session(force=0):
    force = int(force)
    profile_settings = load_profile(profile_id=1)

    if not force ==1 and check_key(profile_settings, 'last_login_time') and profile_settings['last_login_time'] > int(time.time() - 3600) and profile_settings['last_login_success'] == 1:
        return True
    elif force == 1 and not profile_settings['last_login_success'] == 1:
        return False

    token_url_base = '{base_url}/v6/favorites/items'.format(base_url=CONST_API_URL)
    token_parameter = 'oauth_consumer_key=key&oauth_signature_method=HMAC-SHA1&oauth_verifier=' + unicode(profile_settings['resource_verifier']) + '&oauth_token={token}&oauth_version=1.0&oauth_timestamp={timestamp}&oauth_nonce={nonce}&count=1&expand=false&expandlist=false&maxResults=1&offset=0'

    url_encoded = api_oauth_encode(type="GET", base_url=token_url_base, parameters=token_parameter)

    download = api_download(url=url_encoded, type='get', headers=None, data=None, json_data=False, return_json=False)
    data = download['data']
    code = download['code']

    if not code or not code == 200:
        login_result = api_login()

        if not login_result['result']:
            return False

    try:
        query = "UPDATE `vars` SET `last_login_time`={last_login_time}, `last_login_success`=1 WHERE profile_id={profile_id}".format(last_login_time=int(time.time()),profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)
    except:
        pass

    return True

def api_list_watchlist():
    return None

def api_login():
    creds = get_credentials()
    username = creds['username']
    password = creds['password']

    query = "UPDATE `vars` SET `cookies`='', `resource_key`='', `resource_secret`='', `resource_verifier`='' WHERE profile_id={profile_id}".format(profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

    profile_settings = load_profile(profile_id=1)

    request_token_url = '{base_url}/OAuth/GetRequestToken'.format(base_url=CONST_BASE_URL)

    oauth = OAuth1('key', client_secret='secret', callback_uri='null')

    download = api_download(url=request_token_url, type='post', headers=None, data=None, json_data=False, return_json=False, auth=oauth)
    data = download['data']
    code = download['code']

    credentials = parse_qs(data)

    resource_owner_key = credentials.get('oauth_token')[0]
    resource_owner_secret = credentials.get('oauth_token_secret')[0]

    login_url = '{base_url}/account/applogin'.format(base_url=CONST_BASE_URL)

    session_post_data = {
        "username": username,
        "password": password,
    }

    headers = {
        'content-type': 'application/x-www-form-urlencoded'
    }

    download = api_download(url=login_url, type='post', headers=headers, data=session_post_data, json_data=False, return_json=False)
    data = download['data']
    code = download['code']

    if code != 200 and code != 302:
        return { 'code': code, 'data': data, 'result': False }

    authorization_url = "{base_url}/OAuth/Authorize?oauth_token={token}".format(base_url=CONST_BASE_URL, token=resource_owner_key)

    download = api_download(url=authorization_url, type='get', headers=None, data=None, json_data=False, return_json=False, allow_redirects=False)
    data = download['data']
    code = download['code']

    regex = r"oauth_verifier=([a-zA-Z0-9]+)"
    matches = re.finditer(regex, data, re.MULTILINE)

    resource_verifier = ''

    try:
        for match in matches:
           resource_verifier = match.group(1)
    except:
        pass

    if len(resource_verifier) == 0:
        return { 'code': code, 'data': data, 'result': False }

    access_token_url = '{base_url}/OAuth/GetAccessToken'.format(base_url=CONST_BASE_URL)

    oauth = OAuth1('key', client_secret='secret', callback_uri='null', resource_owner_key=resource_owner_key, resource_owner_secret=resource_owner_secret, verifier=resource_verifier)

    download = api_download(url=access_token_url, type='post', headers=None, data=None, json_data=False, return_json=False, auth=oauth)
    data = download['data']
    code = download['code']

    credentials = parse_qs(data)

    try:
        resource_owner_key = credentials.get('oauth_token')[0]
        resource_owner_secret = credentials.get('oauth_token_secret')[0]
    except:
        return { 'code': code, 'data': data, 'result': False }

    query = "UPDATE `vars` SET `resource_key`='{resource_key}', `resource_secret`='{resource_secret}', `resource_verifier`='{resource_verifier}' WHERE profile_id={profile_id}".format(resource_key=resource_owner_key, resource_secret=resource_owner_secret, resource_verifier=resource_verifier, profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

    return { 'code': code, 'data': data, 'result': True }

def api_mix(list1, list2, list3=None):
    if list3:
        i,j,k = iter(list1), iter(list2), iter(list3)
        result = [item for sublist in zip(i,j,k) for item in sublist]
        result += [item for item in i]
        result += [item for item in j]
        result += [item for item in k]
    else:
        i,j = iter(list1), iter(list2)
        result = [item for sublist in zip(i,j) for item in sublist]
        result += [item for item in i]
        result += [item for item in j]

    return result

def api_oauth_encode(type, base_url, parameters):
    profile_settings = load_profile(profile_id=1)

    base_url_encode = quote(base_url, safe='')

    nonce = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(6))
    token_timestamp = int(time.time())

    parameters = parameters.format(token=profile_settings['resource_key'], timestamp=token_timestamp, nonce=nonce)

    parsed_parameters = parse_qs(parameters, keep_blank_values=True)
    encode_string = ''

    for parameter in sorted(parsed_parameters):
        encode_string += quote(unicode(parameter).replace(" ", "%2520") + "=" + unicode(parsed_parameters[parameter][0]).replace(" ", "%2520") + "&", safe='%')

    if encode_string.endswith("%26"):
        encode_string = encode_string[:-len("%26")]

    base_string = '{type}&{token_url_base_encode}&{token_parameter_encode}'.format(type=type, token_url_base_encode=base_url_encode, token_parameter_encode=encode_string)
    base_string_bytes = base_string.encode('utf-8')
    key = 'secret&{key}'.format(key=profile_settings['resource_secret'])
    key_bytes = key.encode('utf-8')

    hashed = hmac.new(key_bytes, base_string_bytes, sha1)
    signature = quote(base64.b64encode(hashed.digest()).decode(), safe='')

    url = '{token_url_base}?{token_parameter}&oauth_signature={signature}'.format(token_url_base=base_url, token_parameter=parameters, signature=signature)

    return url

def api_play_url(type, channel=None, id=None, video_data=None, test=False, from_beginning=0, pvr=0):
    playdata = {'path': '', 'license': '', 'info': ''}

    if not api_get_session():
        return None

    from_beginning = int(from_beginning)
    pvr = int(pvr)
    profile_settings = load_profile(profile_id=1)

    friendly = ''

    query = "SELECT assetid FROM `channels` WHERE id='{channel}'".format(channel=channel)
    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    if data:
        for row in data:
            friendly = row['assetid']

    if not test and not pvr == 1:
        counter = 0

        while not xbmc.Monitor().abortRequested() and counter < 5:
            profile_settings = load_profile(profile_id=1)

            if profile_settings['test_running'] == 0:
                break

            counter += 1

            query = "UPDATE `vars` SET `last_playing`={last_playing} WHERE profile_id={profile_id}".format(last_playing=int(time.time()),profile_id=1)
            query_settings(query=query, return_result=False, return_insert=False, commit=True)

            if xbmc.Monitor().waitForAbort(1):
                break

        if xbmc.Monitor().abortRequested():
            return playdata

        if type == 'channel' and friendly:
            channel_url = '{base_url}/v6/epg/locations/{friendly}/live/1?fromDate={date}'.format(base_url=CONST_API_URL, friendly=friendly, date=datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S"))

            download = api_download(url=channel_url, type='get', headers=None, data=None, json_data=False, return_json=True)
            data = download['data']
            code = download['code']

            if not code or not code == 200 or not data:
                return playdata

            for row in data:
                if not check_key(row, 'Channel') or not check_key(row, 'Locations'):
                    return playdata

                for row2 in row['Locations']:
                    id = row2['LocationId']

        if not id:
            return playdata

        if not type == 'vod':
            token_url_base = '{base_url}/v6/epg/location/{location}'.format(base_url=CONST_API_URL, location=id)
        else:
            token_url_base = '{base_url}/v6/playnow/ondemand/0/{location}'.format(base_url=CONST_API_URL, location=id)

        token_parameter = 'oauth_token={token}&oauth_consumer_key=key&oauth_signature_method=HMAC-SHA1&oauth_version=1.0&oauth_timestamp={timestamp}&oauth_nonce={nonce}'
        url_encoded = api_oauth_encode(type="GET", base_url=token_url_base, parameters=token_parameter)

        download = api_download(url=url_encoded, type='get', headers=None, data=None, json_data=False, return_json=True)
        data = download['data']
        code = download['code']

        if not code or not code == 200 or not data:
            return playdata

        if type == 'vod':
            if not check_key(data, 'VideoInformation'):
                return playdata

            info = data['VideoInformation']
            token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/VOD/{id}'.format(base_url=CONST_API_URL, id=info['Id'])
            timeshift = info['Id']
        else:
            info = data

            timeshift = ''

            if check_key(info, 'VodContentId') and len(unicode(info['VodContentId'])) > 0:
                token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/VOD/{id}'.format(base_url=CONST_API_URL, id=info['VodContentId'])
                timeshift = info['VodContentId']

                if type == 'channel' and channel and friendly:
                    if not settings.getBool(key='ask_start_from_beginning') or not gui.yes_no(message=_.START_FROM_BEGINNING, heading=info['Title']):
                        token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/Live/{friendly}'.format(base_url=CONST_API_URL, friendly=friendly)
                        timeshift = channel

            elif type == 'channel' and channel and friendly:
                token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/Live/{friendly}'.format(base_url=CONST_API_URL, friendly=friendly)
                timeshift = channel
            else:
                token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/Replay/{id}'.format(base_url=CONST_API_URL, id=id)
                timeshift = id
    else:
        if type == 'channel' and channel and friendly:
            token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/Live/{friendly}'.format(base_url=CONST_API_URL, friendly=friendly)
            timeshift = channel
        else:
            token_url_base = '{base_url}/v6/stream/handshake/Widevine/dash/Replay/{id}'.format(base_url=CONST_API_URL, id=id)
            timeshift = id

    token_parameter = 'oauth_token={token}&oauth_consumer_key=key&oauth_signature_method=HMAC-SHA1&playerName=NLZIET%20Meister%20Player%20Web&profile=default&maxResolution=&timeshift=' + unicode(timeshift) + '&oauth_version=1.0&oauth_timestamp={timestamp}&oauth_nonce={nonce}'
    url_encoded = api_oauth_encode(type="GET", base_url=token_url_base, parameters=token_parameter)

    download = api_download(url=url_encoded, type='get', headers=None, data=None, json_data=False, return_json=True)
    data = download['data']
    code = download['code']

    if not code or not code == 200 or not data or not check_key(data, 'uri'):
        return playdata

    license = data
    path = data['uri']

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

    if not len(unicode(license)) > 0:
        return playdata

    playdata = {'path': path, 'license': license, 'info': info}

    return playdata

def api_process_vod(data):
    data = api_mix(data['Items']['npo'], data['Items']['rtl'], data['Items']['sbs'])

    items = []

    for row in data:
        item = {}

        if not check_key(row, 'Type'):
            continue

        if row['Type'] == 'Vod':
            key = 'VideoTile'
        elif row['Type'] == 'Epg':
            key = 'EpgTile'
        elif row['Type'] == 'Serie':
            key = 'SerieTile'
        else:
            continue

        if not check_key(row, key):
            continue

        entry = row[key]

        if not check_key(entry, 'Id') or (not check_key(entry, 'Titel') and (not check_key(entry, 'Serie') or not check_key(entry['Serie'], 'Titel'))):
            continue

        id = entry['Id']
        basetitle = ''
        desc = ''
        start = ''
        duration = 0
        image = ''

        if check_key(entry, 'Serie') and check_key(entry['Serie'], 'Titel'):
            basetitle = entry['Serie']['Titel']

        if check_key(entry, 'Titel'):
            if len(entry['Titel']) > 0 and basetitle != entry['Titel']:
                if len(basetitle) > 0:
                    basetitle += ": " + entry['Titel']
                else:
                    basetitle = entry['Titel']

        if check_key(entry, 'Omschrijving'):
            desc = entry['Omschrijving']

        if check_key(entry, 'Duur'):
            duration = entry['Duur']

        if check_key(entry, 'AfbeeldingUrl'):
            image = entry['AfbeeldingUrl']

            if not 'http' in image:
                image_split = image.rsplit('/', 1)

                if len(image_split) == 2:
                    image = '{image_url}/thumbnails/hd1080/{image}'.format(image_url=CONST_IMAGE_URL, image=image.rsplit('/', 1)[1])
                else:
                    image = '{image_url}/{image}'.format(image_url=CONST_IMAGE_URL, image=image)

        if check_key(entry, 'Uitzenddatum'):
            start = entry['Uitzenddatum']

        item['id'] = id
        item['title'] = basetitle
        item['description'] = desc
        item['duration'] = duration
        item['type'] = row['Type']
        item['icon'] = image
        item['start'] = start

        items.append(item)

    return items

def api_remove_from_watchlist():
    return None

def api_search(query):
    if not api_get_session():
        return None

    file = "cache" + os.sep + "search_" + clean_filename(query) + ".json"

    if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
        data = load_file(file=file, isJSON=True)
    else:
        search_url = '{base_url}/v6/search/v2/combined?searchterm={query}&maxSerieResults=99999999&maxVideoResults=99999999&expand=true&expandlist=true'.format(base_url=CONST_API_URL, query=query)

        download = api_download(url=search_url, type='get', headers=None, data=None, json_data=False, return_json=True)
        data = download['data']
        code = download['code']

        if code and code == 200 and data and settings.getBool(key='enable_cache'):
            write_file(file=file, data=data, isJSON=True)

    if not data:
        return None

    items = []

    if check_key(data, 'Series'):
        for row in data['Series']:
            item = {}

            if not check_key(row, 'SerieId') or not check_key(row, 'Name'):
                continue

            desc = ''
            image = ''

            if check_key(row, 'Omschrijving'):
                desc = row['Omschrijving']

            if check_key(row, 'ProgrammaAfbeelding'):
                image = row['ProgrammaAfbeelding']

                if not 'http' in image:
                    image_split = image.rsplit('/', 1)

                    if len(image_split) == 2:
                        image = '{image_url}/thumbnails/hd1080/{image}'.format(image_url=CONST_IMAGE_URL, image=image.rsplit('/', 1)[1])
                    else:
                        image = '{image_url}/{image}'.format(image_url=CONST_IMAGE_URL, image=image)

            item['id'] = row['SerieId']
            item['title'] = row['Name']
            item['description'] = desc
            item['duration'] = 0
            item['type'] = 'Serie'
            item['icon'] = image

            items.append(item)

    if check_key(data, 'Videos'):
        for row in data['Videos']:
            item = {}

            if not check_key(row, 'Video') or not check_key(row['Video'], 'VideoId') or not check_key(row['Video'], 'VideoType') or (not check_key(row, 'Titel') and (not check_key(row, 'Serie') or not check_key(row['Serie'], 'Titel'))):
                continue

            id = row['Video']['VideoId']

            if row['Video']['VideoType'] == 'VOD':
                type = 'VideoTile'
            elif row['Video']['VideoType'] == 'Replay':
                type = 'EpgTile'
            elif row['Video']['VideoType'] == 'Serie':
                type = 'SerieTile'
            else:
                continue

            basetitle = ''
            desc = ''
            start = ''
            duration = 0
            image = ''

            if check_key(row, 'Serie') and check_key(row['Serie'], 'Titel'):
                basetitle = row['Serie']['Titel']

            if check_key(row, 'Titel'):
                if len(row['Titel']) > 0 and basetitle != row['Titel']:
                    if len(basetitle) > 0:
                        basetitle += ": " + row['Titel']
                    else:
                        basetitle = row['Titel']

            if check_key(row, 'Omschrijving'):
                desc = row['Omschrijving']

            if check_key(row, 'Duur'):
                duration = row['Duur']

            if check_key(row, 'AfbeeldingUrl'):
                image = row['AfbeeldingUrl']

                if not 'http' in image:
                    image_split = image.rsplit('/', 1)

                    if len(image_split) == 2:
                        image = '{image_url}/thumbnails/hd1080/{image}'.format(image_url=CONST_IMAGE_URL, image=image.rsplit('/', 1)[1])
                    else:
                        image = '{image_url}/{image}'.format(image_url=CONST_IMAGE_URL, image=image)

            if check_key(row, 'Uitzenddatum'):
                start = row['Uitzenddatum']

            item['id'] = id
            item['title'] = basetitle
            item['description'] = desc
            item['duration'] = duration
            item['type'] = type
            item['icon'] = image
            item['start'] = start

            items.append(item)

    return items

def api_sort_episodes(element):
    try:
        return element['episodeNumber']
    except:
        return 0

def api_sort_season(element):
    if element['seriesNumber'].isnumeric():
        return int(element['seriesNumber'])
    else:
        matches = re.findall(r"Seizoen (\d+)", element['seriesNumber'])

        for match in matches:
            return int(match)

        return 0

def api_test_channels(tested=False, channel=None):
    profile_settings = load_profile(profile_id=1)

    if channel:
        channel = unicode(channel)

    try:
        if not profile_settings['last_login_success'] == 1 or not settings.getBool(key='run_tests') or not api_get_session():
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

                playdata = api_play_url(type='channel', channel=id, id=None, test=True)

                if first and not profile_settings['last_login_success']:
                    if test_run:
                        update_prefs()

                    query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                    query_settings(query=query, return_result=False, return_insert=False, commit=True)
                    return 5

                if len(playdata['path']) > 0:
                    CDMHEADERS = {}

                    if check_key(playdata, 'license') and check_key(playdata['license'], 'drmConfig') and check_key(playdata['license']['drmConfig'], 'widevine'):
                        if 'nlznl.solocoo.tv' in playdata['license']['drmConfig']['widevine']['drmServerUrl']:
                            if xbmc.Monitor().waitForAbort(1):
                                return 5

                        if check_key(playdata['license']['drmConfig']['widevine'], 'customHeaders'):
                            for row in playdata['license']['drmConfig']['widevine']['customHeaders']:
                                CDMHEADERS[row] = playdata['license']['drmConfig']['widevine']['customHeaders'][row]

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

                while not xbmc.Monitor().abortRequested() and counter < 5:
                    if xbmc.Monitor().waitForAbort(1):
                        break

                    counter += 1

                    profile_settings = load_profile(profile_id=1)

                    if profile_settings['last_playing'] > int(time.time() - 300):
                        if test_run:
                            update_prefs()

                        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return 5

                if xbmc.Monitor().abortRequested():
                    return 5

                yesterday = datetime.datetime.now() - datetime.timedelta(1)
                fromtime = datetime.datetime.strftime(yesterday, "%Y-%m-%dT%H%M%S")
                channel_url = '{base_url}/v6/epg/locations/{friendly}/live/1?fromDate={date}'.format(base_url=CONST_API_URL, friendly=channeldata['channel_friendly'], date=fromtime)

                download = api_download(url=channel_url, type='get', headers=None, data=None, json_data=False, return_json=True)
                data = download['data']
                code = download['code']

                if code and code == 200 and data:
                    for row in data:
                        if check_key(row, 'Channel') and check_key(row, 'Locations'):
                            for row2 in row['Locations']:
                                program_id = row2['LocationId']

                if program_id:
                    profile_settings = load_profile(profile_id=1)

                    if profile_settings['last_playing'] > int(time.time() - 300):
                        if test_run:
                            update_prefs()

                        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return 5

                    playdata = api_play_url(type='program', channel=id, id=program_id, test=True)

                    if len(playdata['path']) > 0:
                        CDMHEADERS = {}

                        if check_key(playdata, 'license') and check_key(playdata['license'], 'drmConfig') and check_key(playdata['license']['drmConfig'], 'widevine'):
                            if 'nlznl.solocoo.tv' in playdata['license']['drmConfig']['widevine']['drmServerUrl']:
                                if xbmc.Monitor().waitForAbort(1):
                                    return 5

                            if check_key(playdata['license']['drmConfig']['widevine'], 'customHeaders'):
                                for row in playdata['license']['drmConfig']['widevine']['customHeaders']:
                                    CDMHEADERS[row] = playdata['license']['drmConfig']['widevine']['customHeaders'][row]

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

                if not xbmc.Monitor().abortRequested():
                    query = "UPDATE `vars` SET `last_tested`='{last_tested}' WHERE profile_id={profile_id}".format(last_tested=id,profile_id=1)
                    query_settings(query=query, return_result=False, return_insert=False, commit=True)

                    query = "REPLACE INTO `tests_{profile_id}` VALUES ('{id}', '{live}', '{livebandwidth}', '{replay}', '{replaybandwidth}', '{epg}', '{guide}')".format(profile_id=1, id=id, live=live, livebandwidth=livebandwidth, replay=replay, replaybandwidth=replaybandwidth, epg=epg, guide=guide)
                    query_settings(query=query, return_result=False, return_insert=False, commit=True)

                test_run = True
                counter = 0

                while not xbmc.Monitor().abortRequested() and counter < 15:
                    if xbmc.Monitor().waitForAbort(1):
                        break

                    counter += 1

                    profile_settings = load_profile(profile_id=1)

                    if profile_settings['last_playing'] > int(time.time() - 300):
                        if test_run:
                            update_prefs()

                        query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
                        query_settings(query=query, return_result=False, return_insert=False, commit=True)
                        return 5

                if xbmc.Monitor().abortRequested():
                    return 5

                count += 1
    except:
        if test_run:
            update_prefs()

        count = 5

    query = "UPDATE `vars` SET `test_running`={test_running} WHERE profile_id={profile_id}".format(test_running=0,profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

    return count

def api_vod_download(type, start=0):
    if not api_get_session():
        return None

    if type == "movies":
        url = '{base_url}/v6/tabs/GenreFilms?count=52&expand=true&expandlist=true&maxResults=52&offset={start}'.format(base_url=CONST_API_URL, start=start)
    elif type == "watchahead":
        url = '{base_url}/v6/tabs/VooruitKijken2?count=52&expand=true&expandlist=true&maxResults=52&offset={start}'.format(base_url=CONST_API_URL, start=start)
    elif type == "seriesbinge":
        url = '{base_url}/v6/tabs/SeriesBingewatch?count=52&expand=true&expandlist=true&maxResults=52&offset={start}'.format(base_url=CONST_API_URL, start=start)
    elif type == "mostviewed":
        url = '{base_url}/v6/tabs/MostViewed?count=52&expand=true&expandlist=true&maxResults=52&offset={start}'.format(base_url=CONST_API_URL, start=start)
    elif type == "tipfeed":
        url = '{base_url}/v6/tabs/Tipfeed?count=52&expand=true&expandlist=true&maxResults=52&offset={start}'.format(base_url=CONST_API_URL, start=start)
    else:
        return None

    file = "cache" + os.sep + "vod_" + type + "_" + unicode(start) + ".json"

    if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
        data = load_file(file=file, isJSON=True)
    else:
        download = api_download(url=url, type='get', headers=None, data=None, json_data=False, return_json=True)
        data = download['data']
        code = download['code']

        if code and code == 200 and data and settings.getBool(key='enable_cache'):
            write_file(file=file, data=data, isJSON=True)

    if not data or not check_key(data, 'Items'):
        return None

    return api_process_vod(data=data)

def api_vod_season(series, id):
    if not api_get_session():
        return None

    season = []

    program_url = '{base_url}/v6/series/{series}/seizoenItems?seizoenId={id}&count=99999999&expand=true&expandlist=true&maxResults=99999999&offset=0'.format(base_url=CONST_API_URL, series=series, id=id)
    file = "cache" + os.sep + "vod_series_" + unicode(series) + "_season_" + unicode(id) + ".json"

    if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
        data = load_file(file=file, isJSON=True)
    else:
        download = api_download(url=program_url, type='get', headers=None, data=None, json_data=False, return_json=True)
        data = download['data']
        code = download['code']

        if code and code == 200 and data and settings.getBool(key='enable_cache'):
            write_file(file=file, data=data, isJSON=True)

    if not data:
        return None

    for row in data:
        duration = 0
        ep_id = ''
        desc = ''
        image = ''
        label = ''

        if check_key(row, 'AfleveringTitel') and len(row['AfleveringTitel']) > 0:
            episodeTitle = row['AfleveringTitel']
        else:
            episodeTitle = row['ProgrammaTitel']

        if check_key(row, 'Duur'):
            duration = row['Duur']

        if check_key(row, 'ContentId'):
            ep_id = row['ContentId']

        if check_key(row, 'ProgrammaOmschrijving'):
            desc = row['ProgrammaOmschrijving']

        if check_key(row, 'ProgrammaAfbeelding'):
            image = row['ProgrammaAfbeelding']

            if not 'http' in image:
                image_split = image.rsplit('/', 1)

                if len(image_split) == 2:
                    image = '{image_url}/thumbnails/hd1080/{image}'.format(image_url=CONST_IMAGE_URL, image=image.rsplit('/', 1)[1])
                else:
                    image = '{image_url}/{image}'.format(image_url=CONST_IMAGE_URL, image=image)

        if check_key(row, 'Uitzenddatum'):
            start = row['Uitzenddatum']
            startT = datetime.datetime.fromtimestamp(time.mktime(time.strptime(start, "%Y-%m-%dT%H:%M:%S")))
            startT = convert_datetime_timezone(startT, "UTC", "UTC")

            if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
                label += '{weekday} {day} {month} {yearhourminute} '.format(weekday=date_to_nl_dag(startT), day=startT.strftime("%d"), month=date_to_nl_maand(startT), yearhourminute=startT.strftime("%Y %H:%M"))
            else:
                label += startT.strftime("%A %d %B %Y %H:%M ").capitalize()

        if check_key(row, 'SeizoenVolgnummer'):
            label += unicode(row['SeizoenVolgnummer'])

        if check_key(row, 'AfleveringVolgnummer'):
            if len(label) > 0:
                label += "."

            label += unicode(row['AfleveringVolgnummer'])

        if len(label) > 0:
            label += " - "

        label += episodeTitle

        season.append({'label': label, 'id': ep_id, 'start': start, 'duration': duration, 'title': episodeTitle, 'seasonNumber': row['SeizoenVolgnummer'], 'episodeNumber': row['AfleveringVolgnummer'], 'description': desc, 'image': image})

    season[:] = sorted(season, key=api_sort_episodes)

    return season

def api_vod_seasons(id):
    if not api_get_session():
        return None

    seasons = []

    program_url = '{base_url}/v6/series/{id}/fullWithSeizoenen?count=99999999&expand=true&expandlist=true&maxResults=99999999&offset=0'.format(base_url=CONST_API_URL, id=id)
    file = "cache" + os.sep + "vod_seasons_" + unicode(id) + ".json"

    if settings.getBool(key='enable_cache') and not is_file_older_than_x_minutes(file=ADDON_PROFILE + file, minutes=10):
        data = load_file(file=file, isJSON=True)
    else:
        download = api_download(url=program_url, type='get', headers=None, data=None, json_data=False, return_json=True)
        data = download['data']
        code = download['code']

        if code and code == 200 and data and settings.getBool(key='enable_cache'):
            write_file(file=file, data=data, isJSON=True)

    if not data or not check_key(data, 'Serie'):
        return None

    season_count = 0
    type = 'seasons'

    if check_key(data, 'SeizoenenForSerie'):
        for row in data['SeizoenenForSerie']:
            season_count += 1

            seasons.append({'id': row['SeizoenId'], 'seriesNumber': row['Titel'], 'description': data['Serie']['Omschrijving'], 'image': data['Serie']['ProgrammaAfbeelding']})

    if check_key(data, 'ItemsForSeizoen') and season_count < 2:
        seasons = []
        type = 'episodes'

        for row in data['ItemsForSeizoen']:
            duration = 0
            ep_id = ''
            desc = ''
            image = ''
            start = ''
            label = ''

            if check_key(row, 'AfleveringTitel'):
                episodeTitle = row['AfleveringTitel']
            else:
                episodeTitle = row['ProgrammaTitel']

            if check_key(row, 'Duur'):
                duration = row['Duur']

            if check_key(row, 'ContentId'):
                ep_id = row['ContentId']

            if check_key(row, 'ProgrammaOmschrijving'):
                desc = row['ProgrammaOmschrijving']

            if check_key(row, 'ProgrammaAfbeelding'):
                image = row['ProgrammaAfbeelding']

                if not 'http' in image:
                    image_split = image.rsplit('/', 1)

                    if len(image_split) == 2:
                        image = '{image_url}/thumbnails/hd1080/{image}'.format(image_url=CONST_IMAGE_URL, image=image.rsplit('/', 1)[1])
                    else:
                        image = '{image_url}/{image}'.format(image_url=CONST_IMAGE_URL, image=image)

            if check_key(row, 'Uitzenddatum'):
                start = row['Uitzenddatum']

            if check_key(row, 'SeizoenVolgnummer'):
                label += unicode(row['SeizoenVolgnummer'])

            if check_key(row, 'AfleveringVolgnummer'):
                if len(label) > 0:
                    label += "."

                label += unicode(row['AfleveringVolgnummer'])

            if len(label) > 0:
                label += " - "

            label += episodeTitle

            seasons.append({'label': label, 'id': ep_id, 'start': start, 'duration': duration, 'title': episodeTitle, 'seasonNumber': row['SeizoenVolgnummer'], 'episodeNumber': row['AfleveringVolgnummer'], 'description': desc, 'image': image})

    if type == 'seasons':
        seasons[:] = sorted(seasons, key=api_sort_season)
    elif type == 'episodes':
        seasons[:] = sorted(seasons, key=api_sort_episodes)

    return {'program': data['Serie'], 'type': type, 'seasons': seasons}
    
def api_watchlist_listing():
    return None