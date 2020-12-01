#!/usr/bin/env python3
import http.client
import json
import base64
import string
import sys
import os
import os.path
import time
import urllib.request, urllib.parse, urllib.error
import ssl

# Global stuff

host = "rt.fastly.com"
ssl._create_default_https_context = ssl._create_unverified_context

def main():

    if len(sys.argv) < 2:
        print("Usage: Sid Refresh_Interval")
        exit()

    if os.environ.get('Fkey') == 'None':
        print("Please set your API key to environment variable Fkey")
        exit()

    sid = sys.argv[1]
    interval = int(sys.argv[2])
    key = os.environ['Fkey']

    # total_edge_bytes = 0
    # total_origin_bytes = 0
    # total_origin_nlc_bytes = 0

    # get a first timestamp and waste the request
    fullURL_RT = "/v1/channel/" + sid + "/ts/h/limit/1" + '?' + urllib.parse.urlencode({'kind' : "origin_insights"})
    requestHead = {'Fastly-Key' : key}

    connection = http.client.HTTPSConnection(host, 443)
    connection.request('GET', fullURL_RT, None, requestHead)

    response = connection.getresponse()
    Stats = response.read()

    # parse results
    StatsOI = json.loads(Stats)
    ts = StatsOI['Timestamp']

    time.sleep(2)

    count = 90 * 24 * 3600
    # usr_input = ''
    while count > 0:
        count -= 1
        origin_bytes = 0
        origin_nlc_bytes = 0
        edge_bytes = 0
        nlc_2xx = 0
        nlc_4xx = 0

        # Fetch origin insight stats
        fullURL_OI = "/v1/channel/" + sid + "/ts/" + str(ts) + '?' + urllib.parse.urlencode({'kind' : "origin_insights"})
        print ("full URL OI: " + str(fullURL_OI) + "\n")
        connection = http.client.HTTPSConnection(host, 443)
        connection.request('GET', fullURL_OI, None, requestHead)
        response = connection.getresponse()
        # print("status: " + str(response.status) + " --- reason: " + str(response.reason))
        Stats = response.read()
        StatsOI = {}
        StatsOI = json.loads(Stats)
        #"timestamp, backend name, backend ip, responses, status_200, status_404, resp_body_bytes"

        # Fetch RT stats
        fullURL_RT = "/v1/channel/" + sid + "/ts/" + str(ts)
        print ("full URL RT: " + str(fullURL_RT) + "\n")
        connection_rt = http.client.HTTPSConnection(host, 443)
        connection_rt.request('GET', fullURL_RT, None, requestHead)
        response_rt = connection_rt.getresponse()
        Stats_rt = response_rt.read()
        StatsJson_rt = {}
        StatsJson_rt = json.loads(Stats_rt)

        ts = StatsOI["Timestamp"]
        j = 0
        while (j < len(StatsOI["Data"])):
            try:
                for p, q in list(StatsOI["Data"][j]['aggregated'].items()):
                    if p == "0bjcorHbsfDndwaycOKYW4--F_Nearline_BlobStore":
                        for data in list(q.values()):
                            origin_nlc_bytes = origin_nlc_bytes + data['resp_body_bytes'] + data['resp_header_bytes']
                            if 'status_2xx' in list(data.keys()):
                                nlc_2xx += data['status_2xx']
                            if 'status_4xx' in list(data.keys()):
                                nlc_4xx += data['status_4xx']
                    elif p == "0bjcorHbsfDndwaycOKYW4--BWI":
                        for data in list(q.values()):
                            origin_bytes = origin_bytes + data['resp_body_bytes'] + data['resp_header_bytes']
            except Exception as e:
                print("Something went wrong with OI Stats: " + str(e))
            j += 1
        j = 0
        while (j < len(StatsJson_rt["Data"])):
            try:
                edge_bytes = edge_bytes + StatsJson_rt["Data"][j]["aggregated"]["edge_resp_header_bytes"] + StatsJson_rt["Data"][j]["aggregated"]["edge_resp_body_bytes"]
            except Exception as e:
                print("Something went wrong with RT Stats: " + str(e))
            j += 1

        try:
            # total_origin_bytes = total_origin_bytes + origin_bytes
            # total_origin_nlc_bytes = total_origin_nlc_bytes + origin_nlc_bytes
            # total_edge_bytes = total_edge_bytes + edge_bytes
            origin_offload = float((1 - (float(origin_bytes) / float(edge_bytes)))*100)

            print("Origin bytes: " + str(origin_bytes) + " - Origin NLC Bytes: " + str(origin_nlc_bytes)+ " - Edge Bytes: " + str(edge_bytes))
            print("Origin offload: "  + str(round(origin_offload, 2)) + " %")

            log_data = {'timestamp': ts,
                        'origin_nlc_bytes': origin_nlc_bytes,
                        'origin_bytes': origin_bytes,
                        'edge_bytes': edge_bytes,
                        'origin_offload': round(origin_offload, 2),
                        'nlc_2xx': nlc_2xx,
                        'nlc_4xx': nlc_4xx}

            # Fetch RT stats
            fullURL_log = "/receiver/v1/http/ZaVnC4dhaV0AUzY94VouvZOLQ47923eHhrWvLYW75rAed7dyhQ1o4_pkh-M18MFDc9Us1MdIDheTHlLJh3knjgFZvqgyqspYUICM1Q5wya6KcWDKhAF_rg=="
            # print "full URL RT: " + fullURL_RT + "\n"
            headers = {"Content-type": "application/json", "Accept": "text/plain"}
            connection_log = http.client.HTTPSConnection("endpoint3.collection.us2.sumologic.com", 443)
            connection_log.request('POST', fullURL_log, json.dumps(log_data), headers)
            response_log = connection_log.getresponse()
            print("response from log collector: " + str(response_log.status) + " , reason: " + response_log.reason)
        except Exception as e:
            print("Something went wrong : " + str(e))
        time.sleep(interval)

if __name__ == '__main__':
  main()