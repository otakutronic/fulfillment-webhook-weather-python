# -*- coding:utf8 -*-
# !/usr/bin/env python
# Copyright 2017 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

from urllib.parse import urlparse, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import requests
from xml.dom import minidom

import json
import os
import re

from flask import Flask
from flask import request
from flask import make_response

# Flask app should start in global layout
app = Flask(__name__)


@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    if req.get("result").get("action")=="yahooWeatherForecast":
        baseurl = "https://query.yahooapis.com/v1/public/yql?"
        yql_query = makeYqlQuery(req)
        if yql_query is None:
           return {}
        yql_url = baseurl + urlencode({'q': yql_query}) + "&format=json"
        result = urlopen(yql_url).read()
        data = json.loads(result)
        res = makeWebhookResult(data)
    elif req.get("result").get("action")=="getjoke":
        baseurl = "http://api.icndb.com/jokes/random"
        result = urlopen(baseurl).read()
        data = json.loads(result)
        res = makeWebhookResultForGetJoke(data)
    elif req.get("result").get("action")=="WikipediaSearch":
        baseurl = "https://en.wikipedia.org/w/api.php?"
        yql_query = makeYqlQueryWiki(req)
        if yql_query is None:
           return {}
        query = urlencode({'search': yql_query})
        wiki_query = {'action':'opensearch', 'format': 'xml',
                  'namespace': '0', 'limit': '1', 'redirects':'resolve', 'warningsaserror':'1', 'utf8': '1'}
        yql_url = baseurl + urlencode(wiki_query) + "&" + query
        result = urlopen(yql_url).read().decode("utf8")
        res = get_title(result)
    else:
        return {}
 
    return res

def get_title(data):
    xmldoc = minidom.parseString(data)
    url = xmldoc.getElementsByTagName('Text')[0].childNodes[0].data
    title = url
    return title

def makeYqlQueryWiki(req):
    result = req.get("result")
    parameters = result.get("parameters")
    query = parameters.get("phrase")
    if query is None:
        return None
    print ('QUERY' + query)
    return query


def makeYqlQuery(req):
    result = req.get("result")
    parameters = result.get("parameters")
    city = parameters.get("geo-city")
    if city is None:
        return None

    return "select * from weather.forecast where woeid in (select woeid from geo.places(1) where text='" + city + "')"

def get_answer(title):
    baseurl = "https://en.wikipedia.org/w/api.php?"

    query = title.strip().replace(" ", "+")
    wiki_query = {'action':'query', 'format': 'xml', 'prop': 'extracts',
                  'list': '', 'redirects': '1', 'exintro': '', 'explaintext': ''}
    yql_url = baseurl + urlencode(wiki_query) + "&titles=" + query
    print ("ANSWER URL = " + yql_url)
    result = requests.get(yql_url).text
    print ("RESULT:\n" + result)
    res = makeWebhookResultForWiki(result)
    return res

def makeWebhookResultForWiki(data):
    xmldoc = minidom.parseString(data)
    extract = xmldoc.getElementsByTagName('extract')[0].childNodes[0].data

    speech = extract

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-wikipedia-webhook"
    }

def makeWebhookResultForGetJoke(data):
    valueString = data.get('value')
    joke = valueString.get('joke')
    speechText = joke
    displayText = joke
    return {
        "speech": speechText,
        "displayText": displayText,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }

def makeWebhookResult(data):
    query = data.get('query')
    if query is None:
        return {}

    result = query.get('results')
    if result is None:
        return {}

    channel = result.get('channel')
    if channel is None:
        return {}

    item = channel.get('item')
    location = channel.get('location')
    units = channel.get('units')
    if (location is None) or (item is None) or (units is None):
        return {}

    condition = item.get('condition')
    if condition is None:
        return {}

    # print(json.dumps(item, indent=4))

    speech = "Today the weather in " + location.get('city') + ": " + condition.get('text') + \
             ", And the temperature is " + condition.get('temp') + " " + units.get('temperature')

    print("Response:")
    print(speech)

    return {
        "speech": speech,
        "displayText": speech,
        # "data": data,
        # "contextOut": [],
        "source": "apiai-weather-webhook-sample"
    }


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    print("Starting app on port %d" % port)

    app.run(debug=False, port=port, host='0.0.0.0')
