import _strptime
import datetime, time, xbmc

from resources.lib.base.l1 import uaparser
from resources.lib.base.l1.constants import DEFAULT_USER_AGENT
from resources.lib.base.l2 import settings
from resources.lib.base.l2.log import log 
from resources.lib.base.l3.language import _
from resources.lib.base.l3.util import check_key, convert_datetime_timezone, date_to_nl_dag, date_to_nl_maand, load_profile, query_epg, query_settings
from resources.lib.base.l4 import gui
from resources.lib.base.l4.session import Session
from resources.lib.base.l5 import inputstream
from resources.lib.constants import CONST_BASE_HEADERS

try:
    unicode
except NameError:
    unicode = str

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
    try:
        if check_key(login_result['data'], 'error') and login_result['data']['error'] == 'toomany':
            gui.ok(message=_.TOO_MANY_DEVICES, heading=_.LOGIN_ERROR_TITLE)
        else:
            gui.ok(message=_.LOGIN_ERROR, heading=_.LOGIN_ERROR_TITLE)
    except:
        gui.ok(message=_.LOGIN_ERROR, heading=_.LOGIN_ERROR_TITLE)

def plugin_post_login():
    pass

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

    if playdata['info']:
        if check_key(playdata['info'], 'params'):
            if check_key(playdata['info']['params'], 'start') and check_key(playdata['info']['params'], 'end'):
                startT = datetime.datetime.fromtimestamp(time.mktime(time.strptime(playdata['info']['params']['start'], "%Y-%m-%dT%H:%M:%SZ")))
                endT = datetime.datetime.fromtimestamp(time.mktime(time.strptime(playdata['info']['params']['end'], "%Y-%m-%dT%H:%M:%SZ")))

                info['duration'] = int((endT - startT).total_seconds())

                if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
                    info['label1'] = '{weekday} {day} {month} {yearhourminute} '.format(weekday=date_to_nl_dag(startT), day=startT.strftime("%d"), month=date_to_nl_maand(startT), yearhourminute=startT.strftime("%Y %H:%M"))
                else:
                    info['label1'] = startT.strftime("%A %d %B %Y %H:%M ").capitalize()

                info['label1'] += " - "

        if playdata['title']:
            info['label1'] += playdata['title'] + ' - '

        if check_key(playdata['info'], 'title'):
            info['label1'] += playdata['info']['title']

        if check_key(playdata['info'], 'descriptiondescription'):
            info['description'] = playdata['info']['description']

        if check_key(playdata['info'], 'images') and check_key(playdata['info']['images'][0], 'url'):
            info['image'] = playdata['info']['images'][0]['url']
            info['image_large'] = playdata['info']['images'][0]['url']

        if check_key(playdata['info'], 'params'):
            if check_key(playdata['info']['params'], 'credits'):
                for castmember in playdata['info']['params']['credits']:
                    if castmember['role'] == "Actor":
                        info['cast'].append(castmember['person'])
                    elif castmember['role'] == "Director":
                        info['director'].append(castmember['person'])
                    elif castmember['role'] == "Writer":
                        info['writer'].append(castmember['person'])

            if check_key(playdata['info']['params'], 'genres'):
                for genre in playdata['info']['params']['genres']:
                    info['genres'].append(genre['title'])

            if check_key(playdata['info']['params'], 'duration'):
                info['duration'] = playdata['info']['params']['duration']

            epcode = ''

            if check_key(playdata['info']['params'], 'seriesSeason'):
                epcode += 'S' + unicode(playdata['info']['params']['seriesSeason'])

            if check_key(playdata['info']['params'], 'seriesEpisode'):
                epcode += 'E' + unicode(playdata['info']['params']['seriesEpisode'])

            if check_key(playdata['info']['params'], 'episodeTitle'):
                info['label2'] = playdata['info']['params']['episodeTitle']

                if len(epcode) > 0:
                    info['label2'] += " (" + epcode + ")"
            elif check_key(playdata['info'], 'title'):
                info['label2'] = playdata['info']['title']

            if check_key(playdata['info']['params'], 'channelId'):
                query = "SELECT name FROM `channels` WHERE id='{channel}'".format(channel=playdata['info']['params']['channelId'])
                data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

                if data:
                    for row in data:
                        info['label2'] += " - "  + row['name']

    return info

def plugin_process_playdata(playdata):
    profile_settings = load_profile(profile_id=1)

    CDMHEADERS = CONST_BASE_HEADERS
    CDMHEADERS['User-Agent'] = profile_settings['user_agent']

    if check_key(playdata, 'license'):
        item_inputstream = inputstream.Widevine(
            license_key = playdata['license'],
        )
    else:
        item_inputstream = inputstream.MPD()

    return item_inputstream, CDMHEADERS

def plugin_renew_token(data):
    return None

def plugin_vod_subscription_filter():
    return None

def plugin_process_watchlist(data):
    items = []

    return items

def plugin_process_watchlist_listing(data, id=None):
    items = []

    return items

def proxy_get_match(path):
    if ".mpd" in path:
        return True

    return False

def proxy_get_session(proxy):
    return Session(cookies_key='cookies', save_cookies=False)

def proxy_get_url(proxy):
    return proxy._stream_url + str(proxy.path)

def proxy_xml_mod(xml):
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

    user_agent = profile_settings['user_agent']

    if len(user_agent) == 0:
        user_agent = DEFAULT_USER_AGENT

    browser_name = uaparser.detect(user_agent)['browser']['name']
    browser_version = uaparser.detect(user_agent)['browser']['version']
    os_name = uaparser.detect(user_agent)['os']['name']
    os_version = uaparser.detect(user_agent)['os']['version']

    query = "UPDATE `vars` SET `browser_name`='{browser_name}', `browser_version`='{browser_version}', `os_name`='{os_name}', `os_version`='{os_version}', `user_agent`='{user_agent}' WHERE profile_id={profile_id}".format(browser_name=browser_name, browser_version=browser_version, os_name=os_name, os_version=os_version, user_agent=user_agent, profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)