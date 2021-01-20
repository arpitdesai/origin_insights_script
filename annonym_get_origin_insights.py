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

def ascii_encode_dict(data):
    ascii_encode = lambda x: x.encode('ascii') if isinstance(x, str) else x
    return dict(list(map(ascii_encode, pair)) for pair in list(data.items()))

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

    # get a first timestamp and waste the request
    fullURL_RT = "/v1/channel/" + sid + "/ts/h/limit/1" + '?' + urllib.parse.urlencode({'kind' : "origin_insights"})
    requestHead = {'Fastly-Key' : key}

    connection = http.client.HTTPSConnection(host, 443)
    connection.request('GET', fullURL_RT, None, requestHead)

    response = connection.getresponse()
    Stats = response.read()

    # parse results
    StatsOI = json.loads(Stats)
    ts = int(StatsOI["Timestamp"])

    time.sleep(2)

    count = 30 * 24 * 3600
    while (count > 0):
        count -= 1
        edge_req = 0
        edge_bytes = 0
        east_origin_req = 0
        east_origin_bytes = 0
        west_origin_bytes = 0
        west_origin_req = 0
        
        try:
            # Fetch origin insight stats
            fullURL_OI = "/v1/channel/" + sid + "/ts/" + str(ts) + '?' + urllib.parse.urlencode({'kind' : "origin_insights"})
            # print ("full URL OI: " + str(fullURL_OI) + "\n")
            connection = http.client.HTTPSConnection(host, 443)
            connection.request('GET', fullURL_OI, None, requestHead)
            response = connection.getresponse()
            Stats = response.read()
            StatsOI = {}
            StatsOI = json.loads(Stats)
            #"timestamp, backend name, backend ip, responses, status_200, status_404, resp_body_bytes"


            # Fetch RT stats
            fullURL_RT = "/v1/channel/" + sid + "/ts/" + str(ts)
            # print ("full URL RT: " + str(fullURL_RT) + "\n")
            connection_rt = http.client.HTTPSConnection(host, 443)
            connection_rt.request('GET', fullURL_RT, None, requestHead)
            response_rt = connection_rt.getresponse()
            Stats_rt = response_rt.read()
            StatsJson_rt = {}
            StatsJson_rt = json.loads(Stats_rt)
        except Exception as e:
            print("Something went wrong : " + str(e))

        ts = int(StatsOI["Timestamp"])
        j = 0
        while (j < len(StatsOI["Data"])):
            try:
                for p, q in list(StatsOI["Data"][j]['aggregated'].items()):
                    if p == "<SID>-<East coast Backend Name>":
                        for o in list(q.values()):
                            east_origin_bytes += o['resp_body_bytes'] + o['resp_header_bytes']
                            east_origin_req += o['responses']
                    elif p == "<SID>-<West coast Backend Name":
                        for o in list(q.values()):
                            west_origin_bytes += o['resp_body_bytes'] + o['resp_header_bytes']
                            west_origin_req += o['responses']
            except Exception as e:
                print("Something went wrong OI Stats : " + str(e))
            j += 1
        j = 0
        while (j < len(StatsJson_rt["Data"])):
            try:
                edge_bytes += StatsJson_rt["Data"][j]["aggregated"]["edge_resp_header_bytes"] + StatsJson_rt["Data"][j]["aggregated"]["edge_resp_body_bytes"]
                edge_req += StatsJson_rt["Data"][j]["aggregated"]["edge_requests"]
            except Exception as e:
                print("Something went wrong RT Stats : " + str(e))
            j += 1
        
        try:
            
            log_data = {'timestamp': ts,
                        'east_origin_bw': east_origin_bytes,
                        'west_origin_bw': west_origin_bytes,
                        'east_origin_req': east_origin_req,
                        'west_origin_req': west_origin_req,
                        'edge_bytes': edge_bytes,
                        'edge_req': edge_req}

            # Fetch RT stats
            fullURL_log = "YOUR HTTP LOGGING ENDPOINT URL (Sumologic can create HTTP endpoints)"
            #print ("full URL RT: " + str(fullURL_RT) + "\n")
            headers = {"Content-type": "application/json", "Accept": "text/plain"}
            connection_log = http.client.HTTPSConnection("endpoint3.collection.us2.sumologic.com", 443)
            connection_log.request('POST', fullURL_log, json.dumps(log_data), headers)
        except Exception as e:
            print("Something went wrong : " + str(e))
        time.sleep(interval)

if __name__ == '__main__':
  main()
