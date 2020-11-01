import _strptime

import datetime, json, os, pytz, re, string, sys, time, xbmc, xbmcplugin

from fuzzywuzzy import fuzz
from resources.lib.api import API
from resources.lib.base import plugin, gui, settings
from resources.lib.base.constants import ADDON_ID, ADDON_PROFILE
from resources.lib.base.exceptions import Error
from resources.lib.base.language import _
from resources.lib.base.log import log
from resources.lib.base.util import check_key, convert_datetime_timezone, create_playlist, date_to_nl_dag, date_to_nl_maand, get_credentials, load_file, load_prefs, load_profile, load_tests, query_epg, query_settings, set_credentials, write_file
from resources.lib.constants import CONST_BASE_HEADERS, CONST_ONLINE_SEARCH, CONST_VOD_CAPABILITY, CONST_WATCHLIST
from resources.lib.util import plugin_ask_for_creds, plugin_login_error, plugin_post_login, plugin_process_info, plugin_process_playdata, plugin_process_watchlist, plugin_process_watchlist_listing, plugin_renew_token, plugin_vod_subscription_filter

try:
    unicode
except NameError:
    unicode = str

try:
    from sqlite3 import dbapi2 as sqlite
except:
    from pysqlite2 import dbapi2 as sqlite

ADDON_HANDLE = int(sys.argv[1])
api = API()
api._abortRequested = False
backend = ''

@plugin.route('')
def home(**kwargs):
    profile_settings = load_profile(profile_id=1)

    if profile_settings['first_boot'] == 1:
        first_boot()

    folder = plugin.Folder()

    if len(profile_settings['pswd']) > 0:
        folder.add_item(label=_(_.LIVE_TV, _bold=True),  path=plugin.url_for(func_or_url=live_tv))
        folder.add_item(label=_(_.CHANNELS, _bold=True), path=plugin.url_for(func_or_url=replaytv))

        if settings.getBool('showMoviesSeries'):
            for vod_entry in CONST_VOD_CAPABILITY:
                folder.add_item(label=_(vod_entry['label'], _bold=True), path=plugin.url_for(func_or_url=vod, file=vod_entry['file'], label=vod_entry['label'], start=vod_entry['start'], online=vod_entry['online'], split=vod_entry['split']))

        if CONST_WATCHLIST:
            folder.add_item(label=_(_.WATCHLIST, _bold=True), path=plugin.url_for(func_or_url=watchlist))

        folder.add_item(label=_(_.SEARCH, _bold=True), path=plugin.url_for(func_or_url=search_menu))

    folder.add_item(label=_(_.LOGIN, _bold=True), path=plugin.url_for(func_or_url=login))
    folder.add_item(label=_.SETTINGS, path=plugin.url_for(func_or_url=settings_menu))

    return folder

#Main menu items
@plugin.route()
def login(ask=1, **kwargs):
    ask = int(ask)

    creds = get_credentials()

    if len(creds['username']) < 1 or len(creds['password']) < 1 or ask == 1:
        user_info = plugin_ask_for_creds(creds)

        if user_info['result']:
            set_credentials(username=user_info['username'], password=user_info['password'])

    login_result = api.login()

    if not login_result['result']:
        query = "UPDATE `vars` SET `pswd`='', `last_login_success`='{last_login_success}' WHERE profile_id={profile_id}".format(last_login_success=0, profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        plugin_login_error(login_result)
    else:
        query = "UPDATE `vars` SET `last_login_success`='{last_login_success}' WHERE profile_id={profile_id}".format(last_login_success=1, profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        gui.ok(message=_.LOGIN_SUCCESS)

        plugin_post_login()

    gui.refresh()

@plugin.route()
def live_tv(**kwargs):
    folder = plugin.Folder(title=_.LIVE_TV)

    for row in get_live_channels(addon=settings.getBool(key='enable_simple_iptv')):
        folder.add_item(
            label = row['label'],
            info = {'plot': row['description']},
            art = {'thumb': row['image']},
            path = row['path'],
            playable = row['playable'],
            context = row['context'],
        )

    return folder

@plugin.route()
def replaytv(**kwargs):
    folder = plugin.Folder(title=_.CHANNELS)

    folder.add_item(
        label = _.PROGSAZ,
        info = {'plot': _.PROGSAZDESC},
        path = plugin.url_for(func_or_url=replaytv_alphabetical),
    )

    for row in get_replay_channels():
        folder.add_item(
            label = row['label'],
            info = {'plot': row['description']},
            art = {'thumb': row['image']},
            path = row['path'],
            playable = row['playable'],
        )

    return folder

@plugin.route()
def replaytv_alphabetical(**kwargs):
    folder = plugin.Folder(title=_.PROGSAZ)
    label = _.OTHERTITLES

    folder.add_item(
        label = label,
        info = {'plot': _.OTHERTITLESDESC},
        path = plugin.url_for(func_or_url=replaytv_list, label=label, start=0, character='other'),
    )

    for character in string.ascii_uppercase:
        label = _.TITLESWITH + character

        folder.add_item(
            label = label,
            info = {'plot': _.TITLESWITHDESC + character},
            path = plugin.url_for(func_or_url=replaytv_list, label=label, start=0, character=character),
        )

    return folder

@plugin.route()
def replaytv_list(character, label='', start=0, **kwargs):
    start = int(start)
    folder = plugin.Folder(title=label)

    processed = process_replaytv_list(character=character, start=start)

    if check_key(processed, 'items'):
        folder.add_items(processed['items'])

    if check_key(processed, 'total') and check_key(processed, 'count') and processed['total'] == 51:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(func_or_url=replaytv_list, character=character, label=label, start=start+processed['count']),
        )

    return folder

@plugin.route()
def replaytv_by_day(label='', image='', description='', station='', **kwargs):
    folder = plugin.Folder(title=label)

    for x in range(0, 7):
        curdate = datetime.date.today() - datetime.timedelta(days=x)

        itemlabel = ''

        if x == 0:
            itemlabel = _.TODAY + " - "
        elif x == 1:
            itemlabel = _.YESTERDAY + " - "

        if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
            itemlabel += date_to_nl_dag(curdate=curdate) + curdate.strftime(" %d ") + date_to_nl_maand(curdate=curdate) + curdate.strftime(" %Y")
        else:
            itemlabel += curdate.strftime("%A %d %B %Y").capitalize()

        folder.add_item(
            label = itemlabel,
            info = {'plot': description},
            art = {'thumb': image},
            path = plugin.url_for(func_or_url=replaytv_content, label=itemlabel, day=x, station=station),
        )

    return folder

@plugin.route()
def replaytv_item(label=None, idtitle=None, start=0, **kwargs):
    start = int(start)
    folder = plugin.Folder(title=label)

    processed = process_replaytv_list_content(label=label, idtitle=idtitle, start=start)

    if check_key(processed, 'items'):
        folder.add_items(processed['items'])

    if check_key(processed, 'total') and check_key(processed, 'count') and processed['total'] == 51:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(func_or_url=replaytv_item, label=label, idtitle=idtitle, start=start+processed['count']),
        )

    return folder

@plugin.route()
def replaytv_content(label, day, station='', start=0, **kwargs):
    day = int(day)
    start = int(start)
    folder = plugin.Folder(title=label)

    processed = process_replaytv_content(station=station, day=day, start=start)

    if check_key(processed, 'items'):
        folder.add_items(processed['items'])

    if check_key(processed, 'total') and check_key(processed, 'count') and processed['total'] == 51:
        folder.add_item(
            label = _(_.NEXT_PAGE, _bold=True),
            path = plugin.url_for(func_or_url=replaytv_content, label=label, day=day, station=station, start=start+processed['count']),
        )

    return folder

@plugin.route()
def vod(file, label, start=0, character=None, online=0, split=0, **kwargs):
    start = int(start)
    online = int(online)
    split = int(split)

    if split == 1:
        folder = plugin.Folder(title=_.PROGSAZ)
        label = _.OTHERTITLES

        folder.add_item(
            label = label,
            info = {'plot': _.OTHERTITLESDESC},
            path = plugin.url_for(func_or_url=vod, file=file, label=label, start=start, character='other', online=online, split=0),
        )

        for character in string.ascii_uppercase:
            label = _.TITLESWITH + character

            folder.add_item(
                label = label,
                info = {'plot': _.TITLESWITHDESC + character},
                path = plugin.url_for(func_or_url=vod, file=file, label=label, start=start, character=character, online=online, split=0),
            )

        return folder
    else:
        folder = plugin.Folder(title=label)

        processed = process_vod_content(data=file, start=start, type=label, character=character, online=online)

        if check_key(processed, 'items'):
            folder.add_items(processed['items'])

        if check_key(processed, 'total') and check_key(processed, 'count2') and processed['total'] > processed['count2']:
            folder.add_item(
                label = _(_.NEXT_PAGE, _bold=True),
                path = plugin.url_for(func_or_url=vod, file=file, label=label, start=processed['count2'], character=character, online=online, split=split),
            )

        return folder

@plugin.route()
def vod_series(label, id, **kwargs):
    folder = plugin.Folder(title=label)

    items = []
    context = []

    seasons = api.vod_seasons(id)

    title = label

    if seasons and check_key(seasons, 'seasons'):
        if CONST_WATCHLIST and check_key(seasons, 'watchlist'):
            context.append((_.ADD_TO_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=add_to_watchlist, id=seasons['watchlist'], type='group')), ))

        if seasons['type'] == "seasons":
            for season in seasons['seasons']:
                label = _.SEASON + " " + unicode(season['seriesNumber']).replace('Seizoen ', '')

                items.append(plugin.Item(
                    label = label,
                    info = {'plot': season['description']},
                    art = {
                        'thumb': season['image'],
                        'fanart': season['image']
                    },
                    path = plugin.url_for(func_or_url=vod_season, label=label, series=id, id=season['id']),
                    context = context,
                ))
        else:
            for episode in seasons['seasons']:
                items.append(plugin.Item(
                    label = episode['label'],
                    info = {
                        'plot': episode['description'],
                        'duration': episode['duration'],
                        'mediatype': 'video',
                    },
                    art = {
                        'thumb': episode['image'],
                        'fanart': episode['image']
                    },
                    path = plugin.url_for(func_or_url=play_video, type='vod', channel=None, id=episode['id']),
                    context = context,
                    playable = True,
                ))

        folder.add_items(items)

    return folder

@plugin.route()
def vod_season(label, series, id, **kwargs):
    folder = plugin.Folder(title=label)

    items = []

    season = api.vod_season(series=series, id=id)

    for episode in season:
        items.append(plugin.Item(
            label = episode['label'],
            info = {
                'plot': episode['description'],
                'duration': episode['duration'],
                'mediatype': 'video',
            },
            art = {
                'thumb': episode['image'],
                'fanart': episode['image']
            },
            path = plugin.url_for(func_or_url=play_video, type='vod', channel=None, id=episode['id'], data=json.dumps(episode)),
            playable = True,
        ))

    folder.add_items(items)

    return folder

@plugin.route()
def search_menu(**kwargs):
    folder = plugin.Folder(title=_.SEARCHMENU)
    label = _.NEWSEARCH

    folder.add_item(
        label = label,
        info = {'plot': _.NEWSEARCHDESC},
        path = plugin.url_for(func_or_url=search),
    )

    if CONST_ONLINE_SEARCH:
        folder.add_item(
            label= label + " (Online)",
            path=plugin.url_for(func_or_url=online_search)
        )

    profile_settings = load_profile(profile_id=1)

    for x in range(1, 10):
        try:
            searchstr = profile_settings['search' + unicode(x)]

            if searchstr != '':
                label = unicode(searchstr)
                path = plugin.url_for(func_or_url=search, query=searchstr)

                if CONST_ONLINE_SEARCH:
                    type = profile_settings['search_type' + unicode(x)]

                    if type == 1:
                        label = unicode(searchstr) + ' (Online)'
                        path = plugin.url_for(func_or_url=online_search, query=searchstr)

                folder.add_item(
                    label = label,
                    info = {'plot': _(_.SEARCH_FOR, query=searchstr)},
                    path = path,
                )
        except:
            pass

    return folder

@plugin.route()
def search(query=None, **kwargs):
    items = []

    if not query:
        query = gui.input(message=_.SEARCH, default='').strip()

        if not query:
            return

        if CONST_ONLINE_SEARCH:
            db_query = "UPDATE `vars` SET `search10`=`search9`, `search_type10`=`search_type9`, `search9`=`search8`, `search_type9`=`search_type8`, `search8`=`search7`, `search_type8`=`search_type7`, `search7`=`search6`, `search_type7`=`search_type6`, `search6`=`search5`, `search_type6`=`search_type5`, `search5`=`search4`, `search_type5`=`search_type4`, `search4`=`search3`, `search_type4`=`search_type3`, `search3`=`search2`, `search_type3`=`search_type2`, `search2`=`search1`, `search_type2`=`search_type1`, `search1`='{search1}', `search_type1`={search_type1} WHERE profile_id={profile_id}".format(search1=query, search_type1=0, profile_id=1)
        else:
            db_query = "UPDATE `vars` SET `search10`=`search9`, `search9`=`search8`, `search8`=`search7`, `search7`=`search6`, `search6`=`search5`, `search5`=`search4`, `search4`=`search3`, `search3`=`search2`, `search2`=`search1`, `search1`='{search1}' WHERE profile_id={profile_id}".format(search1=query, profile_id=1)

        query_settings(query=db_query, return_result=False, return_insert=False, commit=False)

    folder = plugin.Folder(title=_(_.SEARCH_FOR, query=query))

    processed = process_replaytv_search(search=query)
    items += processed['items']

    if settings.getBool('showMoviesSeries'):
        for vod_entry in CONST_VOD_CAPABILITY:
            processed = process_vod_content(data=vod_entry['file'], start=vod_entry['start'], search=query, type=vod_entry['label'], online=vod_entry['online'])
            items += processed['items']

    items[:] = sorted(items, key=_sort_replay_items, reverse=True)
    items = items[:25]

    folder.add_items(items)

    return folder

@plugin.route()
def online_search(query=None, **kwargs):
    items = []

    if not query:
        query = gui.input(message=_.SEARCH, default='').strip()

        if not query:
            return

        db_query = "UPDATE `vars` SET `search10`=`search9`, `search_type10`=`search_type9`, `search9`=`search8`, `search_type9`=`search_type8`, `search8`=`search7`, `search_type8`=`search_type7`, `search7`=`search6`, `search_type7`=`search_type6`, `search6`=`search5`, `search_type6`=`search_type5`, `search5`=`search4`, `search_type5`=`search_type4`, `search4`=`search3`, `search_type4`=`search_type3`, `search3`=`search2`, `search_type3`=`search_type2`, `search2`=`search1`, `search_type2`=`search_type1`, `search1`='{search1}', `search_type1`={search_type1} WHERE profile_id={profile_id}".format(search1=query, search_type1=1, profile_id=1)
        query_settings(query=db_query, return_result=False, return_insert=False, commit=False)

    folder = plugin.Folder(title=_(_.SEARCH_FOR, query=query))

    processed = process_vod_content(data=None, start=0, search=query, type='Online', online=1)
    items += processed['items']

    items[:] = sorted(items, key=_sort_replay_items, reverse=True)
    items = items[:25]

    folder.add_items(items)

    return folder

@plugin.route()
def settings_menu(**kwargs):
    folder = plugin.Folder(title=_.SETTINGS)

    folder.add_item(label=_.CHANNEL_PICKER, path=plugin.url_for(func_or_url=channel_picker_menu))
    folder.add_item(label=_.SET_IPTV, path=plugin.url_for(func_or_url=plugin._set_settings_iptv))
    folder.add_item(label=_.SET_KODI, path=plugin.url_for(func_or_url=plugin._set_settings_kodi))
    folder.add_item(label=_.DOWNLOAD_SETTINGS, path=plugin.url_for(func_or_url=plugin._download_settings))
    folder.add_item(label=_.DOWNLOAD_EPG, path=plugin.url_for(func_or_url=plugin._download_epg))
    folder.add_item(label=_.INSTALL_WV_DRM, path=plugin.url_for(func_or_url=plugin._ia_install))
    folder.add_item(label=_.RESET_SESSION, path=plugin.url_for(func_or_url=login, ask=0))
    folder.add_item(label=_.RESET, path=plugin.url_for(func_or_url=reset_addon))
    folder.add_item(label=_.LOGOUT, path=plugin.url_for(func_or_url=logout))

    folder.add_item(label="Addon " + _.SETTINGS, path=plugin.url_for(func_or_url=plugin._settings))

    return folder

@plugin.route()
def channel_picker_menu(**kwargs):
    folder = plugin.Folder(title=_.CHANNEL_PICKER)

    folder.add_item(label=_.LIVE_TV, path=plugin.url_for(func_or_url=channel_picker, type='live'))
    folder.add_item(label=_.CHANNELS, path=plugin.url_for(func_or_url=channel_picker, type='replay'))
    folder.add_item(label=_.SIMPLEIPTV, path=plugin.url_for(func_or_url=channel_picker, type='epg'))

    return folder

@plugin.route()
def channel_picker(type, **kwargs):
    if type=='live':
        title = _.LIVE_TV
        rows = get_live_channels(addon=False, all=True)
    elif type=='replay':
        title = _.CHANNELS
        rows = get_replay_channels(all=True)
    else:
        title = _.SIMPLEIPTV
        rows = get_live_channels(addon=False, all=True)

    folder = plugin.Folder(title=title)
    prefs = load_prefs(profile_id=1)
    results = load_tests(profile_id=1)
    type = unicode(type)

    for row in rows:
        id = unicode(row['channel'])

        if not prefs or not check_key(prefs, id) or prefs[id][type] == 1:
            color = 'green'
        else:
            color = 'red'

        label = _(row['label'], _bold=True, _color=color)

        if results and check_key(results, id):
            if results[id][type] == 1:
                label += _(' (' + _.TEST_SUCCESS + ')', _bold=False, _color='green')
            else:
                label += _(' (' + _.TEST_FAILED + ')', _bold=False, _color='red')
        else:
            label += _(' (' + _.NOT_TESTED + ')', _bold=False, _color='orange')

        if not prefs or not check_key(prefs, id) or prefs[id][type + '_auto'] == 1:
            choice = _(' ,' + _.AUTO_CHOICE + '', _bold=False, _color='green')
        else:
            choice = _(' ,' + _.MANUAL_CHOICE + '', _bold=False, _color='orange')

        label += choice

        folder.add_item(
            label = label,
            art = {'thumb': row['image']},
            path = plugin.url_for(func_or_url=change_channel, type=type, id=id, change=0),
            context = [
                (_.AUTO_CHOICE_SET, 'Container.Update({context_url})'.format(context_url=plugin.url_for(func_or_url=change_channel, type=type, id=id, change=1)), ),
                #(_.TEST_CHANNEL, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=test_channel, channel=id)), ),
            ],
            playable = False,
        )

    return folder

@plugin.route()
def test_channel(channel, **kwargs):
    profile_settings = load_profile(profile_id=1)
    test_running = profile_settings['test_running']

    while not api._abortRequested and not xbmc.Monitor().abortRequested() and test_running == 1:
        query = "UPDATE `vars` SET `last_playing`='{last_playing}' WHERE profile_id={profile_id}".format(last_playing=int(time.time()), profile_id=1)
        query_settings(query=query, return_result=False, return_insert=False, commit=True)

        if xbmc.Monitor().waitForAbort(1):
            api._abortRequested = True
            break

        profile_settings = load_profile(profile_id=1)
        test_running = profile_settings['test_running']

    if api._abortRequested or xbmc.Monitor().abortRequested():
        return None

    query = "UPDATE `vars` SET `last_playing`=0 WHERE profile_id={profile_id}".format(profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)
    api.test_channels(tested=True, channel=channel)

@plugin.route()
def change_channel(type, id, change, **kwargs):
    change = int(change)

    if not id or len(unicode(id)) == 0 or not type or len(unicode(type)) == 0:
        return False

    prefs = load_prefs(profile_id=1)
    id = unicode(id)
    type = unicode(type)

    keys = ['live', 'replay', 'epg']

    mod_pref = {
        'live': 1,
        'live_auto': 1,
        'replay': 1,
        'replay_auto': 1,
        'epg': 1,
        'epg_auto': 1,
    }

    if prefs and check_key(prefs, id):
        for key in keys:
            if key == type:
                continue

            mod_pref[key] = prefs[id][key]
            mod_pref[key + '_auto'] = prefs[id][key + '_auto']

    if change == 0:
        mod_pref[unicode(type) + '_auto'] = 0

        if not check_key(prefs, id):
            mod_pref[type] = 0
        else:
            if prefs[id][type] == 1:
                mod_pref[type] = 0
            else:
                mod_pref[type] = 1
    else:
        mod_pref[unicode(type) + '_auto'] = 1

        results = load_tests(profile_id=1)

        if not results or not check_key(results, id) or not results[id][type] == 1:
            mod_pref[type] = 1
        else:
            mod_pref[type] = 0

    query = "REPLACE INTO `prefs_{profile_id}` VALUES ('{id}', '{live}', '{live_auto}', '{replay}', '{replay_auto}', '{epg}', '{epg_auto}')".format(profile_id=1, id=id, live=mod_pref['live'], live_auto=mod_pref['live_auto'], replay=mod_pref['replay'], replay_auto=mod_pref['replay_auto'], epg=mod_pref['epg'], epg_auto=mod_pref['epg_auto'])
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

    if type == 'epg':
        create_playlist()

    xbmc.executeJSONRPC('{{"jsonrpc":"2.0","id":1,"method":"GUI.ActivateWindow","params":{{"window":"videos","parameters":["plugin://' + unicode(ADDON_ID) + '/?_=channel_picker&type=' + type + '"]}}}}')

@plugin.route()
def reset_addon(**kwargs):
    plugin._reset()
    gui.refresh()

@plugin.route()
def logout(**kwargs):
    if not gui.yes_no(message=_.LOGOUT_YES_NO):
        return

    query = "UPDATE `vars` SET `pswd`='', `username`='' WHERE profile_id={profile_id}".format(profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)
    gui.refresh()

@plugin.route()
def play_video(type=None, channel=None, id=None, data=None, title=None, from_beginning=0, **kwargs):
    from_beginning = int(from_beginning)

    properties = {}

    if not type or not len(unicode(type)) > 0:
        return False

    playdata = api.play_url(type=type, channel=channel, id=id, video_data=data, from_beginning=from_beginning)

    if not playdata or not check_key(playdata, 'path'):
        return False

    playdata['channel'] = channel
    playdata['title'] = title

    item_inputstream, CDMHEADERS = plugin_process_playdata(playdata)

    info = plugin_process_info(playdata)

    if type == 'program':
        properties['seekTime'] = 1
    elif type == 'channel':
        if from_beginning == 1:
            properties['seekTime'] = 1
        elif settings.getBool(key='ask_start_from_beginning'):
            if gui.yes_no(message=_.START_FROM_BEGINNING, heading=info['label2']):
                properties['seekTime'] = 1

    query = "UPDATE `vars` SET `stream_duration`='{stream_duration}' WHERE profile_id={profile_id}".format(stream_duration=info['duration'], profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

    listitem = plugin.Item(
        label = info['label1'],
        label2 = info['label2'],
        art = {
            'thumb': info['image'],
            'fanart': info['image_large']
        },
        info = {
            'credits': info['credits'],
            'cast': info['cast'],
            'writer': info['writer'],
            'director': info['director'],
            'genre': info['genres'],
            'plot': info['description'],
            'duration': info['duration'],
            'mediatype': 'video',
            'year': info['year'],
        },
        properties = properties,
        path = playdata['path'],
        headers = CDMHEADERS,
        inputstream = item_inputstream,
    )

    return listitem

@plugin.route()
def switchChannel(channel_uid, **kwargs):
    global backend

    play_url = 'PlayMedia(pvr://channels/tv/{allchan}/{backend}_{uid}.pvr)'.format(allchan=xbmc.getLocalizedString(19287), backend=backend, uid=unicode(channel_uid))
    xbmc.executebuiltin(play_url)

@plugin.route()
def renew_token(**kwargs):
    data = {}

    for key, value in kwargs.items():
        data[key] = value

    mod_path = plugin_renew_token(data)

    listitem = plugin.Item(
        path = mod_path,
    )

    newItem = listitem.get_li()

    xbmcplugin.addDirectoryItem(ADDON_HANDLE, mod_path, newItem)
    xbmcplugin.endOfDirectory(ADDON_HANDLE, cacheToDisc=False)

    if xbmc.Monitor().waitForAbort(0.1):
        return None

@plugin.route()
def add_to_watchlist(id, type, **kwargs):
    if api.add_to_watchlist(id=id, type=type):
        gui.notification(_.ADDED_TO_WATCHLIST)
    else:
        gui.notification(_.ADD_TO_WATCHLIST_FAILED)

@plugin.route()
def remove_from_watchlist(id, **kwargs):
    if api.remove_from_watchlist(id=id):
        gui.refresh()
        gui.notification(_.REMOVED_FROM_WATCHLIST)
    else:
        gui.notification(_.REMOVE_FROM_WATCHLIST_FAILED)

@plugin.route()
def watchlist(**kwargs):
    folder = plugin.Folder(title=_.WATCHLIST)

    data = api.list_watchlist()

    if data:
        processed = plugin_process_watchlist(data=data)

        if processed:
            folder.add_items(processed)

    return folder

@plugin.route()
def watchlist_listing(label, id, search=0, **kwargs):
    search = int(search)

    folder = plugin.Folder(title=label)

    data = api.watchlist_listing(id)

    if search == 0:
        id = None

    if data:
        processed = plugin_process_watchlist_listing(data=data, id=id)

        if processed:
            folder.add_items(processed)

    return folder

#Support functions
def first_boot():
    if gui.yes_no(message=_.SET_IPTV):
        try:
            plugin._set_settings_iptv()
        except:
            pass
    if gui.yes_no(message=_.SET_KODI):
        try:
            plugin._set_settings_kodi()
        except:
            pass

    query = "UPDATE `vars` SET `first_boot`='{first_boot}' WHERE profile_id={profile_id}".format(first_boot=0, profile_id=1)
    query_settings(query=query, return_result=False, return_insert=False, commit=True)

def get_live_channels(addon=False, all=False):
    global backend
    channels = []
    pvrchannels = []

    query = "SELECT * FROM `channels`"

    if settings.getBool('disableErotica'):
        query += " WHERE `erotica`=0"

    query += " ORDER BY `channelno` ASC"

    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    prefs = load_prefs(profile_id=1)

    if data:
        if addon:
            query_addons = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddons", "params": {"type": "xbmc.pvrclient"}}'))

            if check_key(query_addons, 'result') and check_key(query_addons['result'], 'addons'):
                addons = query_addons['result']['addons']
                backend = addons[0]['addonid']

                query_channel = json.loads(xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "PVR.GetChannels", "params": {"channelgroupid": "alltv", "properties" :["uniqueid"]},"id": 1}'))

                if check_key(query_channel, 'result') and check_key(query_channel['result'], 'channels'):
                    pvrchannels = query_channel['result']['channels']

        for row in data:
            path = plugin.url_for(func_or_url=play_video, type='channel', channel=row['id'], id=row['assetid'], _is_live=True)
            playable = True

            for channel in pvrchannels:
                if channel['label'] == row['name']:
                    channel_uid = channel['uniqueid']
                    path = plugin.url_for(func_or_url=switchChannel, channel_uid=channel_uid)
                    playable = False
                    break

            id = unicode(row['id'])

            if all or not prefs or not check_key(prefs, id) or prefs[id]['live'] == 1:
                image_path = ADDON_PROFILE + "images" + os.sep + unicode(row['id']) + ".png"

                if os.path.isfile(image_path):
                    image = image_path
                else:
                    image = row['icon']

                channels.append({
                    'label': row['name'],
                    'channel': row['id'],
                    'chno': row['channelno'],
                    'description': row['description'],
                    'image': image,
                    'path':  path,
                    'playable': playable,
                    'context': [
                        (_.START_BEGINNING, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=play_video, type='channel', channel=row['id'], id=row['assetid'], from_beginning=1)), ),
                    ],
                })

    return channels

def get_replay_channels(all=False):
    channels = []

    query = "SELECT * FROM `channels`"

    if settings.getBool('disableErotica'):
        query += " WHERE `erotica`=0"

    query += " ORDER BY `channelno` ASC"

    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    prefs = load_prefs(profile_id=1)

    if data:
        for row in data:
            id = unicode(row['id'])

            if all or not prefs or not check_key(prefs, id) or prefs[id]['replay'] == 1:
                image_path = ADDON_PROFILE + "images" + os.sep + unicode(row['id']) + ".png"

                if os.path.isfile(image_path):
                    image = image_path
                else:
                    image = row['icon']

                channels.append({
                    'label': row['name'],
                    'channel': row['id'],
                    'chno': row['channelno'],
                    'description': row['description'],
                    'image': image,
                    'path': plugin.url_for(func_or_url=replaytv_by_day, image=row['icon'], description=row['description'], label=row['name'], station=row['id']),
                    'playable': False,
                    'context': [],
                })

    return channels

def process_replaytv_list(character, start=0):
    profile_settings = load_profile(profile_id=1)

    now = datetime.datetime.now(pytz.timezone("Europe/Amsterdam"))
    sevendays = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")) - datetime.timedelta(days=7)
    nowstamp = int((now - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())
    sevendaysstamp = int((sevendays - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())

    query = "SELECT * FROM `channels`"

    if settings.getBool('disableErotica'):
        query += " WHERE `erotica`=0"

    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    channels_ar2 = {}

    if data:
        for row in data:
            channels_ar2[unicode(row['id'])] = row['name']

    prefs = load_prefs(profile_id=1)
    channels_ar = []

    if prefs:
        for row in prefs:
            currow = prefs[row]

            if not check_key(channels_ar2, unicode(currow['id'])):
                continue

            if currow['replay'] == 1:
                channels_ar.append(row)

    channels = "', '".join(map(str, channels_ar))

    query = "SELECT idtitle, title, icon FROM `epg` WHERE first='{first}' AND start < {nowstamp} AND end > {sevendaysstamp} AND channel IN ('{channels}') GROUP BY idtitle LIMIT 51 OFFSET {start}".format(first=character, nowstamp=nowstamp, sevendaysstamp=sevendaysstamp, channels=channels, start=start)
    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    start = int(start)
    items = []
    item_count = 0

    if not data:
        return {'items': items, 'count': item_count, 'total': 0}

    for row in data:
        if item_count == 51:
            break

        item_count += 1

        label = row['title']
        idtitle = row['idtitle']

        items.append(plugin.Item(
            label = label,
            art = {
                'thumb': row['icon'],
                'fanart': row['icon']
            },
            path = plugin.url_for(func_or_url=replaytv_item, label=label, idtitle=idtitle, start=0),
        ))

    returnar = {'items': items, 'count': item_count, 'total': len(data)}

    return returnar

def process_replaytv_search(search):
    profile_settings = load_profile(profile_id=1)

    now = datetime.datetime.now(pytz.timezone("Europe/Amsterdam"))
    sevendays = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")) - datetime.timedelta(days=7)
    nowstamp = int((now - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())
    sevendaysstamp = int((sevendays - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())

    query = "SELECT * FROM `channels`"

    if settings.getBool('disableErotica'):
        query += " WHERE `erotica`=0"

    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    channels_ar2 = {}

    if data:
        for row in data:
            channels_ar2[unicode(row['id'])] = row['name']

    prefs = load_prefs(profile_id=1)
    channels_ar = []

    if prefs:
        for row in prefs:
            currow = prefs[row]

            if not check_key(channels_ar2, unicode(currow['id'])):
                continue

            if currow['replay'] == 1:
                channels_ar.append(row)

    channels = "', '".join(map(str, channels_ar))

    query = "SELECT idtitle, title, icon FROM `epg` WHERE start < {nowstamp} AND end > {sevendaysstamp} AND channel IN ('{channels}') GROUP BY idtitle".format(nowstamp=nowstamp, sevendaysstamp=sevendaysstamp, channels=channels)
    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    items = []

    if not data:
        return {'items': items}

    for row in data:
        fuzz_set = fuzz.token_set_ratio(row['title'], search)
        fuzz_partial = fuzz.partial_ratio(row['title'], search)
        fuzz_sort = fuzz.token_sort_ratio(row['title'], search)

        if (fuzz_set + fuzz_partial + fuzz_sort) > 160:
            label = row['title'] + ' (ReplayTV)'
            idtitle = row['idtitle']

            items.append(plugin.Item(
                label = label,
                art = {
                    'thumb': row['icon'],
                    'fanart': row['icon']
                },
                properties = {"fuzz_set": fuzz_set, "fuzz_sort": fuzz_sort, "fuzz_partial": fuzz_partial, "fuzz_total": fuzz_set + fuzz_partial + fuzz_sort},
                path = plugin.url_for(func_or_url=replaytv_item, label=label, idtitle=idtitle, start=0),
            ))

    returnar = {'items': items}

    return returnar

def process_replaytv_content(station, day=0, start=0):
    profile_settings = load_profile(profile_id=1)

    day = int(day)
    start = int(start)
    curdate = datetime.date.today() - datetime.timedelta(days=day)

    startDate = convert_datetime_timezone(datetime.datetime(curdate.year, curdate.month, curdate.day, 0, 0, 0), "Europe/Amsterdam", "UTC")
    endDate = convert_datetime_timezone(datetime.datetime(curdate.year, curdate.month, curdate.day, 23, 59, 59), "Europe/Amsterdam", "UTC")
    startTimeStamp = int((startDate - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())
    endTimeStamp = int((endDate - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())

    query = "SELECT * FROM `epg` WHERE channel='{channel}' AND start >= {startTime} AND start <= {endTime} LIMIT 51 OFFSET {start}".format(channel=station, startTime=startTimeStamp, endTime=endTimeStamp, start=start)
    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    items = []
    item_count = 0

    if not data:
        return {'items': items, 'count': item_count, 'total': 0}

    for row in data:
        if item_count == 51:
            break

        context = []
        item_count += 1

        startT = datetime.datetime.fromtimestamp(row['start'])
        startT = convert_datetime_timezone(startT, "Europe/Amsterdam", "Europe/Amsterdam")
        endT = datetime.datetime.fromtimestamp(row['end'])
        endT = convert_datetime_timezone(endT, "Europe/Amsterdam", "Europe/Amsterdam")

        if endT < (datetime.datetime.now(pytz.timezone("Europe/Amsterdam")) - datetime.timedelta(days=7)):
            continue

        label = startT.strftime("%H:%M") + " - " + row['title']

        description = row['description']

        duration = int((endT - startT).total_seconds())

        program_image = row['icon']
        program_image_large = row['icon']

        if CONST_WATCHLIST:
            context.append((_.ADD_TO_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=add_to_watchlist, id=row['program_id'], type='item')), ))

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
            path = plugin.url_for(func_or_url=play_video, type='program', channel=row['channel'], id=row['program_id']),
            context = context,
            playable = True,
        ))

    returnar = {'items': items, 'count': item_count, 'total': len(data)}

    return returnar

def process_replaytv_list_content(label, idtitle, start=0):
    profile_settings = load_profile(profile_id=1)

    start = int(start)

    now = datetime.datetime.now(pytz.timezone("Europe/Amsterdam"))
    sevendays = datetime.datetime.now(pytz.timezone("Europe/Amsterdam")) - datetime.timedelta(days=7)
    nowstamp = int((now - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())
    sevendaysstamp = int((sevendays - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds())

    query = "SELECT * FROM `channels`"

    if settings.getBool('disableErotica'):
        query += " WHERE `erotica`=0"

    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    channels_ar2 = {}

    if data:
        for row in data:
            channels_ar2[unicode(row['id'])] = row['name']

    prefs = load_prefs(profile_id=1)
    channels_ar = []

    if prefs:
        for row in prefs:
            currow = prefs[row]

            if not check_key(channels_ar2, unicode(currow['id'])):
                continue

            if currow['replay'] == 1:
                channels_ar.append(row)

    channels = "', '".join(map(str, channels_ar))

    query = "SELECT * FROM `epg` WHERE idtitle='{idtitle}' AND start < {nowstamp} AND end > {sevendaysstamp} AND channel IN ('{channels}') LIMIT 51 OFFSET {start}".format(idtitle=idtitle, nowstamp=nowstamp, sevendaysstamp=sevendaysstamp, channels=channels, start=start)
    data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    items = []
    item_count = 0

    if not data:
        return {'items': items, 'count': item_count, 'total': 0}

    for row in data:
        if item_count == 51:
            break

        context = []
        item_count += 1

        startT = datetime.datetime.fromtimestamp(row['start'])
        startT = convert_datetime_timezone(startT, "Europe/Amsterdam", "Europe/Amsterdam")
        endT = datetime.datetime.fromtimestamp(row['end'])
        endT = convert_datetime_timezone(endT, "Europe/Amsterdam", "Europe/Amsterdam")

        if xbmc.getLanguage(xbmc.ISO_639_1) == 'nl':
            itemlabel = '{weekday} {day} {month} {yearhourminute} '.format(weekday=date_to_nl_dag(startT), day=startT.strftime("%d"), month=date_to_nl_maand(startT), yearhourminute=startT.strftime("%Y %H:%M"))
        else:
            itemlabel = startT.strftime("%A %d %B %Y %H:%M ").capitalize()

        itemlabel += row['title'] + " (" + channels_ar2[unicode(row['channel'])] + ")"

        description = row['description']
        duration = int((endT - startT).total_seconds())
        program_image = row['icon']
        program_image_large = row['icon']

        if CONST_WATCHLIST:
            context.append((_.ADD_TO_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=add_to_watchlist, id=row['program_id'], type='item')), ))

        items.append(plugin.Item(
            label = itemlabel,
            info = {
                'plot': description,
                'duration': duration,
                'mediatype': 'video',
            },
            art = {
                'thumb': program_image,
                'fanart': program_image_large
            },
            path = plugin.url_for(func_or_url=play_video, type='program', channel=row['channel'], id=row['program_id']),
            playable = True,
            context = context
        ))

    returnar = {'items': items, 'count': item_count, 'total': len(data)}

    return returnar

def process_vod_content(data, start=0, search=None, type=None, character=None, online=0):
    profile_settings = load_profile(profile_id=1)

    subscription_filter = plugin_vod_subscription_filter()

    start = int(start)

    items = []
    count = start
    item_count = 0

    if online == 1:
        if search:
            data = api.search(query=search)
        else:
            data = api.vod_api_download(type=data, start=start)
    else:
        if character:
            query = "SELECT * FROM `{table}` WHERE first='{first}' ORDER BY title ASC LIMIT 999999 OFFSET {start}".format(table=data, first=character, start=start)
        else:
            query = "SELECT * FROM `{table}` ORDER BY title ASC LIMIT 999999 OFFSET {start}".format(table=data, start=start)

        data = query_epg(query=query, return_result=True, return_insert=False, commit=False)

    if not data:
        return {'items': items, 'count': item_count, 'count2': count, 'total': 0}

    for row in data:
        if item_count == 51:
            break

        context = []
        count += 1

        id = row['id']
        label = row['title']

        if subscription_filter and not int(id) in subscription_filter:
            continue

        if search and not online == 1:
            fuzz_set = fuzz.token_set_ratio(label,search)
            fuzz_partial = fuzz.partial_ratio(label,search)
            fuzz_sort = fuzz.token_sort_ratio(label,search)

            if (fuzz_set + fuzz_partial + fuzz_sort) > 160:
                properties = {"fuzz_set": fuzz.token_set_ratio(label,search), "fuzz_sort": fuzz.token_sort_ratio(label,search), "fuzz_partial": fuzz.partial_ratio(label,search), "fuzz_total": fuzz.token_set_ratio(label,search) + fuzz.partial_ratio(label,search) + fuzz.token_sort_ratio(label,search)}
                label = label + " (" + type + ")"
            else:
                continue

        item_count += 1

        properties = []
        description = row['description']
        duration = 0

        if row['duration'] and len(unicode(row['duration'])) > 0:
            duration = int(row['duration'])

        program_image = row['icon']
        program_image_large = row['icon']

        if row['type'] == "show" or row['type'] == "Serie":
            path = plugin.url_for(func_or_url=vod_series, label=label, id=id)
            info = {'plot': description}
            playable = False
        elif row['type'] == "Epg":
            path = plugin.url_for(func_or_url=play_video, type='program', channel=None, id=id)
            info = {'plot': description, 'duration': duration, 'mediatype': 'video'}
            playable = True
        elif row['type'] == "movie" or row['type'] == "Vod":
            path = plugin.url_for(func_or_url=play_video, type='vod', channel=None, id=id)
            info = {'plot': description, 'duration': duration, 'mediatype': 'video'}
            playable = True
        else:
            continue

        if CONST_WATCHLIST:
            context.append((_.ADD_TO_WATCHLIST, 'RunPlugin({context_url})'.format(context_url=plugin.url_for(func_or_url=add_to_watchlist, id=row['id'], type='group')), ))

        items.append(plugin.Item(
            label = label,
            properties = properties,
            info = info,
            art = {
                'thumb': program_image,
                'fanart': program_image_large
            },
            path = path,
            playable = playable,
            context = context
        ))

    total = int(len(data) + start)

    returnar = {'items': items, 'count': item_count, 'count2': count, 'total': total}

    return returnar

def _sort_replay_items(element):
    return element.get_li().getProperty('fuzz_total')