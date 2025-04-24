#!/usr/bin/env python3
#
# mmdb-server is an open source fast API server to lookup IP addresses for their geographic location.
#
# The server is released under the AGPL version 3 or later.
#
# Copyright (C) 2022 Alexandre Dulaunoy

import configparser
import time
from ipaddress import ip_address
import json
from wsgiref.simple_server import make_server
import logging
import signal
import sys
from typing import List, Dict, Any

import falcon
import maxminddb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MMDBServer:
    def __init__(self):
        self.version = "0.5"
        self.config = configparser.ConfigParser()
        self.config.read('etc/server.conf')
        self.mmdb_file = self.config['global'].get('mmdb_file')
        self.pubsub = self.config['global'].getboolean('lookup_pubsub')
        self.port = self.config['global'].getint('port')
        self.country_file = self.config['global'].get('country_file')
        
        self.mmdb_files = self.mmdb_file.split(",")
        self.country_info = self._load_country_info()
        self.mmdbs = self._load_mmdb_databases()
        self.rdb = self._setup_redis() if self.pubsub else None
        self.httpd = None
        self.app = self._setup_app()

    def _load_country_info(self) -> Dict:
        with open(self.country_file) as j:
            return json.load(j)

    def _load_mmdb_databases(self) -> List[Dict[str, Any]]:
        mmdbs = []
        for mmdb_file in self.mmdb_files:
            meta = {}
            meta['reader'] = maxminddb.open_database(mmdb_file, maxminddb.MODE_MEMORY)
            meta['description'] = meta['reader'].metadata().description
            meta['build_db'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(meta['reader'].metadata().build_epoch)
            )
            meta['db_source'] = meta['reader'].metadata().database_type
            meta['nb_nodes'] = meta['reader'].metadata().node_count
            mmdbs.append(meta)
        return mmdbs

    def _setup_redis(self):
        import redis
        return redis.Redis(host='127.0.0.1')

    def _setup_app(self) -> falcon.App:
        app = falcon.App()
        app.add_route('/geolookup/{value}', GeoLookup(self))
        app.add_route('/', MyGeoLookup(self))
        return app

    def validIPAddress(self, IP: str) -> bool:
        try:
            type(ip_address(IP))
            return True
        except ValueError:
            return False

    def pubLookup(self, value: str) -> bool:
        if not self.pubsub or not self.rdb:
            return False
        self.rdb.publish('mmdb-server::lookup', f'{value}')
        return True

    def countryLookup(self, country: str) -> dict:
        if country != 'None' or country is not None or country != 'Unknown':
            if country in self.country_info:
                return self.country_info[country]
        return {}

    def cleanup(self):
        """Cleanup resources before shutdown"""
        logger.info("Starting graceful shutdown...")
        
        # Close MMDB databases
        for mmdb in self.mmdbs:
            try:
                if 'reader' in mmdb:
                    mmdb['reader'].close()
            except Exception as e:
                logger.error(f"Error closing MMDB database: {e}")

        # Close Redis connection
        if self.rdb:
            try:
                self.rdb.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        # Stop the HTTP server
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception as e:
                logger.error(f"Error shutting down HTTP server: {e}")

        logger.info("Cleanup completed")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}")
        self.cleanup()
        sys.exit(0)

    def serve_forever(self):
        """Start the server with signal handling"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        # Start the server
        self.httpd = make_server('', self.port, self.app)
        logger.info(f'Serving on port {self.port}...')
        try:
            self.httpd.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.cleanup()
            sys.exit(1)


class BaseGeoLookup:
    def __init__(self, server: MMDBServer):
        self.server = server

    def process_georesult(self, georesult: Dict, meta: Dict, ip: str) -> Dict:
        """Process georesult based on database type"""
        result = {
            'meta': meta,
            'ip': ip
        }

        # Copy all fields from georesult
        result.update(georesult)

        # Add country info if available
        if 'country' in georesult and 'iso_code' in georesult['country']:
            result['country_info'] = self.server.countryLookup(country=georesult['country']['iso_code'])
        else:
            result['country_info'] = {}

        return result

    def lookup_ip(self, ip: str) -> List[Dict]:
        """Common IP lookup logic"""
        ret = []
        for mmdb in self.server.mmdbs:
            try:
                georesult = mmdb['reader'].get(ip)
                if georesult is None:
                    continue

                m = mmdb.copy()
                del m['reader']
                processed_result = self.process_georesult(georesult, m, ip)
                ret.append(processed_result)
            except Exception as e:
                logger.error(f"Error processing result from {mmdb['db_source']}: {e}")
                continue
        return ret


class GeoLookup(BaseGeoLookup):
    def on_get(self, req, resp, value):
        if not self.server.validIPAddress(value):
            resp.status = falcon.HTTP_422
            resp.media = "IPv4 or IPv6 address is in an incorrect format. Dotted decimal for IPv4 or textual representation for IPv6 are required."
            return

        ua = req.get_header('User-Agent')
        ips = req.access_route
        self.server.pubLookup(value=f'{value} via {ips} using {ua}')
        
        resp.media = self.lookup_ip(value)
        return


class MyGeoLookup(BaseGeoLookup):
    def on_get(self, req, resp):
        ips = req.access_route
        resp.media = self.lookup_ip(ips[0])
        return


def main():
    server = MMDBServer()
    server.serve_forever()


if __name__ == '__main__':
    main()

