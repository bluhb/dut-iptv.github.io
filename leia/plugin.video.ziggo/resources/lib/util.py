import _strptime

import datetime, json, re, sys, xbmc
from resources.lib.base import gui, inputstream, settings
from resources.lib.base.api import api_download
from resources.lib.base.constants import ADDON_ID, DEFAULT_USER_AGENT
from resources.lib.base.language import _
from resources.lib.base.session import Session
from resources.lib.base.util import check_key, convert_datetime_timezone, date_to_nl_dag, date_to_nl_maand, get_credentials, load_file, load_profile, query_epg, query_settings
from resources.lib.constants import CONST_ALLOWED_HEADERS, CONST_BASE_HEADERS, CONST_DEFAULT_CLIENTID

try:
    unicode
except NameError:
    unicode = str

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

def check_entitlements():
    from resources.lib.api import API

    api = API()
    api._abortRequested = False
    profile_settings = load_profile(profile_id=1)

    base_v3 = profile_settings['base_v3']

    if base_v3 == 0:
        media_groups_url = '{mediagroups_url}/lgi-nl-vod-myprime-movies?byHasCurrentVod=true&range=1-1&sort=playCount7%7Cdesc'.format(mediagroups_url=profile_settings['mediagroupsfeeds_url'])
    else:
        media_groups_url = '{mediagroups_url}/crid:~~2F~~2Fschange.com~~2Fdc30ecd3-4701-4993-993b-9ad4ff5fc301?byHasCurrentVod=true&range=1-1&sort=playCount7%7Cdesc'.format(mediagroups_url=profile_settings['mediagroupsfeeds_url'])

    download = api_download(url=media_groups_url, type='get', headers=None, data=None, json_data=False, return_json=True)
    data = download['data']
    code = download['code']

    if not code or not code == 200 or not data or not check_key(data, 'entryCount'):
        gui.ok(message=_.NO_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
        settings.setBool(key='showMoviesSeries', value=False)
        return

    id = data['mediaGroups'][0]['id']

    media_item_url = '{mediaitem_url}/{mediaitem_id}'.format(mediaitem_url=profile_settings['mediaitems_url'], mediaitem_id=id)

    download = api_download(url=media_item_url, type='get', headers=None, data=None, json_data=False, return_json=True)
    data = download['data']
    code = download['code']

    if not code or not code == 200 or not data:
        gui.ok(message=_.NO_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
        settings.setBool(key='showMoviesSeries', value=False)
        return

    if check_key(data, 'videoStreams'):
        urldata = get_play_url(content=data['videoStreams'])

    if (not urldata or not check_key(urldata, 'play_url') or not check_key(urldata, 'locator') or urldata['play_url'] == 'http://Playout/using/Session/Service') and base_v3:
            urldata = {}

            playout_url = '{base_url}/playout/vod/{id}?abrType=BR-AVC-DASH'.format(base_url=profile_settings['base_url'], id=id)
            download = api_download(url=playout_url, type='get', headers=None, data=None, json_data=False, return_json=True)
            data = download['data']
            code = download['code']

            if not code or not code == 200 or not data or not check_key(data, 'url') or not check_key(data, 'contentLocator'):
                gui.ok(message=_.NO_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
                settings.setBool(key='showMoviesSeries', value=False)
                return

            urldata['play_url'] = data['url']
            urldata['locator'] = data['contentLocator']

    if not urldata or not check_key(urldata, 'play_url') or not check_key(urldata, 'locator'):
        gui.ok(message=_.NO_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
        settings.setBool(key='showMoviesSeries', value=False)
        return

    token = api.get_play_token(locator=urldata['locator'], path=urldata['play_url'], force=1)

    if not token or not len(token) > 0:
        gui.ok(message=_.NO_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
        settings.setBool(key='showMoviesSeries', value=False)
        return

    gui.ok(message=_.YES_MOVIES_SERIES, heading=_.CHECKED_ENTITLEMENTS)
    settings.setBool(key='showMoviesSeries', value=True)

    return

def encode_obj(in_obj):
    def encode_list(in_list):
        out_list = []
        for el in in_list:
            out_list.append(encode_obj(el))
        return out_list

    def encode_dict(in_dict):
        out_dict = {}

        if sys.version_info < (3, 0):
            for k, v in in_dict.iteritems():
                out_dict[k] = encode_obj(v)
        else:
            for k, v in in_dict.items():
                out_dict[k] = encode_obj(v)

        return out_dict

    if isinstance(in_obj, unicode):
        return in_obj.encode('utf-8')
    elif isinstance(in_obj, list):
        return encode_list(in_obj)
    elif isinstance(in_obj, tuple):
        return tuple(encode_list(in_obj))
    elif isinstance(in_obj, dict):
        return encode_dict(in_obj)

    return in_obj

def get_image(prefix, content):
    best_image = 0
    image_url = ''

    for images in content:
        if prefix in images['assetTypes']:
            if best_image < 7:
                best_image = 7
                image_url = images['url']
        elif ('HighResPortrait') in images['assetTypes']:
            if best_image < 6:
                best_image = 6
                image_url = images['url']
        elif ('HighResLandscapeShowcard') in images['assetTypes']:
            if best_image < 5:
                best_image = 5
                image_url = images['url']
        elif ('HighResLandscape') in images['assetTypes']:
            if best_image < 4:
                best_image = 4
                image_url = images['url']
        elif (prefix + '-xlarge') in images['assetTypes']:
            if best_image < 3:
                best_image = 3
                image_url = images['url']
        elif (prefix + '-large') in images['assetTypes']:
            if best_image < 2:
                best_image = 2
                image_url = images['url']
        elif (prefix + '-medium') in images['assetTypes']:
            if best_image < 1:
                best_image = 1
                image_url = images['url']

    return image_url

def get_play_url(content):
    profile_settings = load_profile(profile_id=1)

    if profile_settings['base_v3'] == 1 and check_key(content, 'url') and check_key(content, 'contentLocator'):
        return {'play_url': content['url'], 'locator': content['contentLocator']}
    else:
        for stream in content:
            if  'streamingUrl' in stream and 'contentLocator' in stream and 'assetTypes' in stream and 'Orion-DASH' in stream['assetTypes']:
                return {'play_url': stream['streamingUrl'], 'locator': stream['contentLocator']}

    return {'play_url': '', 'locator': ''}

def remove_ac3(xml):
    try:
        result = re.findall(r'<[aA]daptation[sS]et(?:(?!</[aA]daptation[sS]et>)[\S\s])+</[aA]daptation[sS]et>', xml)

        for match in result:
            if "codecs=\"ac-3\"" in match:
                xml = xml.replace(match, "")
    except:
        pass

    return xml

def plugin_ask_for_creds(creds):
    username = gui.input(message=_.ASK_USERNAME, default=creds['username']).strip()

    if not len(username) > 0:
        gui.ok(message=_.EMPTY_USER, heading=_.LOGIN_ERROR_TITLE)
        return {'result': False, 'username': '', 'password': ''}

    password = gui.input(message=_.ASK_PASSWORD, hide_input=True).strip()

    if not len(password) > 0:
        gui.ok(message=_.EMPTY_PASS, heading=_.LOGIN_ERROR_TITLE)
        return {'result': False, 'username': '', 'password': ''}

    return {'result': True, 'username': username, 'password': password}

def plugin_login_error(login_result):
    gui.ok(message=_.LOGIN_ERROR, heading=_.LOGIN_ERROR_TITLE)

def plugin_post_login():
    check_entitlements()

def plugin_process_info(playdata):
    info = {
        'label1': '',
        'label2': '',
        'description': '',
        'image': '',
        'image_large': '',
        'duration': 0,
        'credits': [],
        'cast': [],
        'director': [],
        'writer': [],
        'genres': [],
        'year': '',
    }

    if check_key(playdata, 'info'):
        if check_key(playdata['info'], 'latestBroadcastEndTime') and check_key(playdata['info'], 'latestBroadcastStartTime'):
            startsplit = int(playdata['info']['latestBroadcastStartTime']) // 1000
            endsplit = int(playdata['info']['latestBroadcastEndTime']) // 1000
            duration = endsplit - startsplit

            startT = datetime.datetime.fromtimestamp(startsplit)
            startT = convert_datetime_timezone(startT, "UTC", "UTC")
            endT = datetime.datetime.fromtimestamp(endsplit)
            endT = convert_datetime_timezone(endT, "UTC", "UTC")

            if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
                info['label1'] = '{weekday} {day} {month} {yearhourminute} '.format(weekday=date_to_nl_dag(startT), day=startT.strftime("%d"), month=date_to_nl_maand(startT), yearhourminute=startT.strftime("%Y %H:%M"))
            else:
                info['label1'] = startT.strftime("%A %d %B %Y %H:%M ").capitalize()

        if playdata['title']:
            info['label1'] += playdata['title'] + ' - ' + playdata['info']['title']
        else:
            info['label1'] += playdata['info']['title']

        if check_key(playdata['info'], 'duration'):
            info['duration'] = int(playdata['info']['duration'])
        elif check_key(playdata['info'], 'latestBroadcastStartTime') and check_key(playdata['info'], 'latestBroadcastEndTime'):
            info['duration'] = int(int(playdata['info']['latestBroadcastEndTime']) - int(playdata['info']['latestBroadcastStartTime'])) // 1000

        if check_key(playdata['info'], 'description'):
            info['description'] = playdata['info']['description']

        if check_key(playdata['info'], 'duration'):
            info['duration'] = int(playdata['info']['duration'])

        if check_key(playdata['info'], 'year'):
            info['year'] = int(playdata['info']['year'])

        if check_key(playdata['info'], 'images'):
            info['image'] = get_image("boxart", playdata['info']['images'])
            info['image_large'] = get_image("HighResLandscape", playdata['info']['images'])

            if info['image_large'] == '':
                info['image_large'] = info['image']
            else:
                info['image_large'] += '?w=1920&mode=box'

        if check_key(playdata['info'], 'categories'):
            for categoryrow in playdata['info']['categories']:
                info['genres'].append(categoryrow['title'])

        if check_key(playdata['info'], 'cast'):
            for castrow in playdata['info']['cast']:
                info['cast'].append(castrow)

        if check_key(playdata['info'], 'directors'):
            for directorrow in playdata['info']['directors']:
                info['director'].append(directorrow)

        epcode = ''

        if check_key(playdata['info'], 'seriesNumber'):
            epcode += 'S' + unicode(playdata['info']['seriesNumber'])

        if check_key(playdata['info'], 'seriesEpisodeNumber'):
            epcode += 'E' + unicode(playdata['info']['seriesEpisodeNumber'])

        if check_key(playdata['info'], 'secondaryTitle'):
            info['label2'] = playdata['info']['secondaryTitle']

            if len(epcode) > 0:
                info['label2'] += " (" + epcode + ")"
        else:
            info['label2'] = playdata['info']['title']

        query = "SELECT name FROM `channels` WHERE id='{channel}'".format(channel=playdata['channel'])
        data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

        if data:
            for row in data:
                info['label2'] += " - "  + row['name']

    return info

def plugin_process_playdata(playdata):
    creds = get_credentials()
    profile_settings = load_profile(profile_id=1)

    CDMHEADERS = {
        'User-Agent': profile_settings['user_agent'],
        'X-Client-Id': profile_settings['client_id'] + '||' + profile_settings['user_agent'],
        'X-OESP-Token': profile_settings['access_token'],
        'X-OESP-Username': creds['username'],
        'X-OESP-License-Token': profile_settings['drm_token'],
        'X-OESP-DRM-SchemeIdUri': 'urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
        'X-OESP-Content-Locator': playdata['locator'],
    }

    params = []

    try:
        params.append(('_', 'renew_token'))
        params.append(('path', str(playdata['path']).encode('utf-8')))
        params.append(('locator', str(playdata['locator']).encode('utf-8')))
    except:
        params.append(('_', 'renew_token'))
        params.append(('path', playdata['path']))
        params.append(('locator', playdata['locator']))

    item_inputstream = inputstream.Widevine(
        license_key = playdata['license'],
        media_renewal_url = 'plugin://{0}/?{1}'.format(ADDON_ID, urlencode(encode_obj(params))),
        media_renewal_time = 60,
    )

    return item_inputstream, CDMHEADERS

def plugin_renew_token(data):
    from resources.lib.api import API

    api = API()
    api._abortRequested = False
    api.get_play_token(locator=data['locator'], path=data['path'])

    data['path'] = data['path'].replace("/manifest.mpd", "/")

    splitpath = data['path'].split('/Manifest?device', 1)

    if len(splitpath) == 2:
        data['path'] = splitpath[0] + "/"

    return data['path']

def plugin_process_watchlist(data):
    items = []

    if check_key(data, 'entries'):
        for row in data['entries']:
            context = []

            if check_key(row, 'mediaGroup') and check_key(row['mediaGroup'], 'medium') and check_key(row['mediaGroup'], 'id'):
                currow = row['mediaGroup']
                id = currow['id']
            elif check_key(row, 'mediaItem') and check_key(row['mediaItem'], 'medium') and check_key(row['mediaItem'], 'mediaGroupId'):
                currow = row['mediaItem']
                id = currow['mediaGroupId']
            else:
                continue

            if not check_key(currow, 'title'):
                continue

            context.append((_.REMOVE_FROM_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=remove_from_watchlist, id=id)), ))

            if check_key(currow, 'isReplayTv') and currow['isReplayTv'] == "false":
                if not settings.getBool('showMoviesSeries'):
                    continue

                type = 'vod'
            else:
                type = 'program'

            channel = ''
            mediatype = ''
            duration = ''
            description = ''
            program_image = ''
            program_image_large = ''
            playable = False
            path = ''

            if check_key(currow, 'description'):
                description = currow['description']

            if check_key(currow, 'images'):
                program_image = get_image("boxart", currow['images'])
                program_image_large = get_image("HighResLandscape", currow['images'])

                if program_image_large == '':
                    program_image_large = program_image
                else:
                    program_image_large += '?w=1920&mode=box'

            if currow['medium'] == 'TV':
                if not check_key(currow, 'seriesLinks'):
                    path = plugin.url_for(func_or_url=watchlist_listing, label=currow['title'], id=id, search=0)
                else:
                    path = plugin.url_for(func_or_url=vod_series, label=currow['title'], description=description, image=program_image, image_large=program_image_large, seasons=json.dumps(currow['seriesLinks']))
            elif currow['medium'] == 'Movie':
                if check_key(currow, 'duration'):
                    duration = int(currow['duration'])
                elif check_key(currow, 'startTime') and check_key(currow, 'endTime'):
                    duration = int(int(currow['endTime']) - int(currow['startTime'])) // 1000
                else:
                    duration = 0

                path = plugin.url_for(func_or_url=play_video, type=type, channel=channel, id=currow['id'], title=None)
                playable = True
                mediatype = 'video'

            items.append(plugin.Item(
                label = currow['title'],
                info = {
                    'plot': description,
                    'duration': duration,
                    'mediatype': mediatype,
                },
                art = {
                    'thumb': program_image,
                    'fanart': program_image_large
                },
                path = path,
                playable = playable,
                context = context
            ))

    return items

def plugin_process_watchlist_listing(data, id=None):
    items = []

    if check_key(data, 'listings'):
        for row in data['listings']:
            context = []

            if not check_key(row, 'program'):
                continue

            currow = row['program']

            if not check_key(currow, 'title') or not check_key(row, 'id'):
                continue

            duration = 0

            if check_key(row, 'endTime') and check_key(row, 'startTime'):
                startsplit = int(row['startTime']) // 1000
                endsplit = int(row['endTime']) // 1000
                duration = endsplit - startsplit

                startT = datetime.datetime.fromtimestamp(startsplit)
                startT = convert_datetime_timezone(startT, "UTC", "UTC")
                endT = datetime.datetime.fromtimestamp(endsplit)
                endT = convert_datetime_timezone(endT, "UTC", "UTC")

                if endT < (datetime.datetime.now(pytz.timezone("UTC")) - datetime.timedelta(days=7)):
                    continue

                if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
                    label = '{weekday} {day} {month} {yearhourminute} '.format(weekday=date_to_nl_dag(startT), day=startT.strftime("%d"), month=date_to_nl_maand(startT), yearhourminute=startT.strftime("%Y %H:%M"))
                else:
                    label = startT.strftime("%A %d %B %Y %H:%M ").capitalize()

                label += currow['title']
            else:
                label = currow['title']

            query = "SELECT name FROM `channels` WHERE id='{channel}'".format(channel=currow['stationId'])
            data2 = query_epg(query=query, return_result=True, return_insert=False, commit=False)

            if data2:
                for row2 in data2:
                    label += ' ({station})'.format(station=row2['name'])

            if id:
                context.append((_.ADD_TO_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=add_to_watchlist, id=id, type="group")), ))

            channel = ''
            description = ''
            program_image = ''
            program_image_large = ''

            if check_key(currow, 'description'):
                description = currow['description']

            if check_key(currow, 'duration'):
                duration = int(currow['duration'])

            if check_key(currow, 'images'):
                program_image = get_image("boxart", currow['images'])
                program_image_large = get_image("HighResLandscape", currow['images'])

                if program_image_large == '':
                    program_image_large = program_image
                else:
                    program_image_large += '?w=1920&mode=box'

            items.append(plugin.Item(
                label = label,
                info = {
                    'plot': description,
                    'duration': duration,
                    'mediatype': 'video',
                },
                art = {
                    'thumb': program_image,
                    'fanart': program_image_large
                },
                path = plugin.url_for(func_or_url=play_video, type="program", channel=channel, id=row['id']),
                playable = True,
                context = context
            ))

    return items

def plugin_vod_subscription_filter():
    return None

def proxy_get_match(path):
    if "manifest.mpd" in path or "Manifest" in path:
        return True

    return False

def proxy_get_session(proxy):
    HEADERS = CONST_BASE_HEADERS

    for header in proxy.headers:
        if proxy.headers[header] is not None and header in CONST_ALLOWED_HEADERS:
            HEADERS[header] = proxy.headers[header]

    return Session(headers=HEADERS)

def proxy_get_url(proxy):
    profile_settings = load_profile(profile_id=1)

    return proxy._stream_url + str(proxy.path).replace('WIDEVINETOKEN', profile_settings['drm_token'])

def proxy_xml_mod(xml):
    if settings.getBool(key="disableac3") == True:
        xml = remove_ac3(xml=xml)

    return xml

def service_timer(timer):
    if timer == 'daily':
        pass
    elif timer == 'hourly':
        pass
    elif timer == 'startup':
        pass

def update_settings():
    profile_settings = load_profile(profile_id=1)

    settingsJSON = load_file(file='settings.json', isJSON=True)

    base = settingsJSON['settings']['urls']['base']

    if profile_settings['base_v3'] == 1:
        basethree = settingsJSON['settings']['urls']['alternativeAjaxBase']
    else:
        basethree = base

    complete_base_url = '{base_url}/{country_code}/{language_code}'.format(base_url=basethree, country_code=settingsJSON['settings']['countryCode'], language_code=settingsJSON['settings']['languageCode'])

    try:
        client_id = settingsJSON['client_id']
    except:
        client_id = CONST_DEFAULT_CLIENTID

    user_agent = profile_settings['user_agent']

    if len(user_agent) == 0:
        user_agent = DEFAULT_USER_AGENT

    query = "UPDATE `vars` SET `base_url`='{base_url}', `client_id`='{client_id}', `devices_url`='{devices_url}', `search_url`='{search_url}', `session_url`='{session_url}', `channels_url`='{channels_url}', `token_url`='{token_url}', `widevine_url`='{widevine_url}', `listings_url`='{listings_url}', `mediaitems_url`='{mediaitems_url}', `mediagroupsfeeds_url`='{mediagroupsfeeds_url}', `watchlist_url`='{watchlist_url}', `user_agent`='{user_agent}' WHERE profile_id={profile_id}".format(base_url=complete_base_url + '/web', client_id=client_id, devices_url=settingsJSON['settings']['routes']['devices'].replace(base, basethree), search_url=settingsJSON['settings']['routes']['search'].replace(base, basethree), session_url=settingsJSON['settings']['routes']['session'].replace(base, basethree), channels_url=settingsJSON['settings']['routes']['channels'].replace(base, basethree), token_url='{complete_base_url}/web/license/token'.format(complete_base_url=complete_base_url), widevine_url='{complete_base_url}/web/license/eme'.format(complete_base_url=complete_base_url), listings_url=settingsJSON['settings']['routes']['listings'].replace(base, basethree), mediaitems_url=settingsJSON['settings']['routes']['mediaitems'].replace(base, basethree), mediagroupsfeeds_url=settingsJSON['settings']['routes']['mediagroupsfeeds'].replace(base, basethree), watchlist_url=settingsJSON['settings']['routes']['watchlist'].replace(base, basethree), user_agent=user_agent, profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)