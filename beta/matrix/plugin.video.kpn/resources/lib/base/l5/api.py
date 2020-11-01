import json, xbmc

from resources.lib.base.l4.session import Session

def api_download(url, type, headers=None, data=None, json_data=True, return_json=True, allow_redirects=True, auth=None):
    session = Session(cookies_key='cookies')

    if headers:
        session.headers = headers

    if type == "post" and data:
        if json_data:
            resp = session.post(url, json=data, allow_redirects=allow_redirects, auth=auth)
        else:
            resp = session.post(url, data=data, allow_redirects=allow_redirects, auth=auth)
    else:
        resp = getattr(session, type)(url, allow_redirects=allow_redirects, auth=auth)

    if return_json:
        try:
            returned_data = json.loads(resp.json().decode('utf-8'))
        except:
            try:
                returned_data = resp.json()
            except:
                returned_data = resp.text
    else:
        returned_data = resp.text

    return { 'code': resp.status_code, 'data': returned_data, 'headers': resp.headers }