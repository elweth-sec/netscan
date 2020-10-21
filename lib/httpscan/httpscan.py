from time import sleep
from utils.output import Output

import requests
from bs4 import BeautifulSoup
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

urllib3.disable_warnings()

def httpscan_worker(target, useragent, proxy, timeout):
    httpscan = HTTPScan(target['method'], target['hostname'], target['port'], useragent, proxy, timeout)

    httpscan.get(target['path'])

class HTTPScan:

    def __init__(self, method, hostname, port, useragent, proxy, connect_timeout):
        self.method = method
        self.hostname = hostname
        self.port = port
        self.connect_timeout = connect_timeout
        self.useragent = useragent
        self.proxy = proxy
        self.read_timeout = 60

    def get(self, path, ssl_version=ssl.PROTOCOL_TLSv1_2):
        try:
            url = "{method}://{hostname}:{port}{path}".format(method=self.method, hostname=self.hostname, port=self.port, path=path)

            if self.proxy:
                proxies = {
                    'http': self.proxy,
                    'https': self.proxy,
                }
            else:
                proxies = {}

            headers = {
                'User-Agent': self.useragent,
            }

            session = requests.Session()
            session.mount('https://', SSLAdapter(ssl_version))
            res = session.get(url, timeout=(self.connect_timeout, self.read_timeout), headers=headers, proxies=proxies, verify=False, stream=True)
            response_data = self.parse_response(res)

            response_data['message_type'] = 'http'
            response_data['target'] = url

            Output.write(response_data)    
        except requests.exceptions.ConnectTimeout:
            response_data = None
        except requests.exceptions.ConnectionError:
            response_data = None
        except requests.exceptions.ReadTimeout:
            response_data = None

        return response_data

    def parse_response(self, res):
        code = res.status_code
        headers = res.headers

        server = headers['server'].strip() if 'server' in headers else 'N/A'
        content_type = headers['content-type'].strip() if 'server' in headers else None

        html = ""
        max_size = 1024*1000
        for chunk in res.iter_content(chunk_size=1024, decode_unicode=True):
            if type(chunk) == bytes:
                # Garbage data
                break
            html += chunk
            if len(html) >= max_size:
                break


        return {
            'code': code,
            'server': server,
            'title': self.parse_title(html),
            'content-type': content_type,
        }

    def parse_title(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')

        if title != None and title.string != None:
            return title.string.strip()
        else:
            return 'N/A'

class SSLAdapter(HTTPAdapter):
    '''An HTTPS Transport Adapter that uses an arbitrary SSL version.'''
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version

        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=self.ssl_version)
