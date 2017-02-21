import json

import flask
import httplib2

from apiclient import discovery
from oauth2client import client
import datetime
import re

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from urlparse import urlparse


app = flask.Flask(__name__)


@app.route('/')
def index():
  if 'credentials' not in flask.session:
    return flask.redirect(flask.url_for('oauth2callback'))

  credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
  if credentials.access_token_expired:
    return flask.redirect(flask.url_for('oauth2callback'))
  else:
    http_auth = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http_auth)

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(
      calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
      orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
      print('No upcoming events found.')
      return json.dumps({})
    for event in events:
      start = event['start'].get('dateTime', event['start'].get('date'))
      print(start, event['summary'])
    return json.dumps(events)


@app.route('/phantomjs')
def hacky_get_salsa_cal():
  phantomJS_path='/usr/local/bin/phantomjs'
  salsa_cal_url = 'http://www.salsabythebay.com/salsa-events-calendar/?month=2&myyear=2017'
  js_cal_data = """var raw_js = document.getElementsByTagName('script')[21].text; var fn_src = raw_js.replace(/[\\n\\r]+/g,'') + ' return calendarArray;'; return JSON.stringify(new Function(fn_src)());"""

  driver = webdriver.PhantomJS(executable_path=phantomJS_path)
  driver.get(salsa_cal_url)
  cal_arr = driver.execute_script(js_cal_data)
  driver.close()

  jdata = json.loads(cal_arr, "utf-8")
  pydata = []
  idx = 0
  for jobj in jdata:
    pydata.append({})
    for k,v in jobj.iteritems():
      pydata[idx][k] = v
      # print k, v
    idx = idx + 1
    # print ''
  sfonly = filter(lambda o: o[u'region'] == u'sanfrancisco', pydata)
  return json.dumps(sfonly)


@app.route('/auth/google_oauth2/callback')
def oauth2callback():
  flow = client.flow_from_clientsecrets(
    'client_secrets.json',
    #scope='https://www.googleapis.com/auth/userinfo.email+https://www.googleapis.com/auth/calendar',
    scope='https://www.googleapis.com/auth/calendar',
    #scope='https://www.googleapis.com/auth/drive.metadata.readonly',
    redirect_uri=flask.url_for('oauth2callback', _external=True))
  if 'code' not in flask.request.args:
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
  else:
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    print "credentials:", flask.session['credentials']
    return flask.redirect(flask.url_for('index'))


if __name__ == '__main__':
  import uuid
  app.secret_key = str(uuid.uuid4())
  app.debug = True
  app.run(host='localhost', port=3000)
