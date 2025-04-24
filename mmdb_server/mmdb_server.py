#!/usr/bin/env python3
#
# mmdb-server is an open source fast API server to lookup IP addresses for their
# geographic location.
#
# The server is released under the AGPL version 3 or later.
#
# Copyright (C) 2022 Alexandre Dulaunoy

import configparser
import json
import logging
import signal
import sys
import time
from ipaddress import ip_address
from types import FrameType
from typing import Any, Dict, List, Mapping, NoReturn, Optional, TypedDict
from wsgiref.simple_server import make_server

import falcon
import maxminddb
import redis
from falcon import Request, Response
from maxminddb.reader import Reader

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CountryInfo(TypedDict, total=False):
    name: str
    alpha2: str
    alpha3: str
    numeric: str
    latitude: float
    longitude: float


class MMDBMeta(TypedDict):
    reader: Reader
    description: Mapping[str, str]
    build_db: str
    db_source: str
    nb_nodes: int


class GeoCountry(TypedDict):
    iso_code: str


class GeoResult(TypedDict, total=False):
    country: GeoCountry


class MMDBServer:
    def __init__(self):
        self.version = "0.5"
        self.config = configparser.ConfigParser()
        self.config.read("etc/server.conf")
        self.mmdb_file: str = self.config["global"].get("mmdb_file", "")
        self.pubsub: bool = bool(
            self.config["global"].getboolean("lookup_pubsub", False)
        )
        self.port: int = int(self.config["global"].getint("port", 8080))
        self.country_file: str = self.config["global"].get("country_file", "")

        self.mmdb_files = self.mmdb_file.split(",")
        self.country_info: Dict[str, CountryInfo] = self._load_country_info()
        self.mmdbs: List[MMDBMeta] = self._load_mmdb_databases()
        self.rdb: Optional[redis.Redis[bytes]] = (
            self._setup_redis() if self.pubsub else None
        )
        self.httpd = None
        self.app: falcon.App = self._setup_app()

    def _load_country_info(self) -> Dict[str, CountryInfo]:
        with open(self.country_file) as j:
            return json.load(j)

    def _load_mmdb_databases(self) -> List[MMDBMeta]:
        mmdbs: List[MMDBMeta] = []
        for mmdb_file in self.mmdb_files:
            reader = maxminddb.open_database(mmdb_file, mode=8)
            metadata = reader.metadata()
            meta: MMDBMeta = {
                "reader": reader,
                "description": metadata.description,
                "build_db": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(metadata.build_epoch),
                ),
                "db_source": metadata.database_type,
                "nb_nodes": metadata.node_count,
            }
            mmdbs.append(meta)
        return mmdbs

    def _setup_redis(self) -> redis.Redis[bytes]:
        return redis.Redis(host="127.0.0.1")

    def _setup_app(self) -> falcon.App:
        app = falcon.App()
        app.add_route("/geolookup/{value}", GeoLookup(self))  # type: ignore
        app.add_route("/", MyGeoLookup(self))  # type: ignore
        return app

    def valid_ip_address(self, ip_addr: str) -> bool:
        try:
            ip_address(ip_addr)
            return True
        except ValueError:
            return False

    def pub_lookup(self, value: str) -> bool:
        if not self.pubsub or not self.rdb:
            return False
        self.rdb.publish("mmdb-server::lookup", f"{value}")
        return True

    def country_lookup(self, country: str) -> CountryInfo:
        if country != "Unknown":
            if country in self.country_info:
                return self.country_info[country]
        return {}

    def cleanup(self) -> None:
        """Cleanup resources before shutdown"""
        logger.info("Starting graceful shutdown...")

        # Close MMDB databases
        for mmdb in self.mmdbs:
            try:
                if "reader" in mmdb:
                    mmdb["reader"].close()
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

    def signal_handler(self, signum: int, frame: Optional[FrameType]) -> NoReturn:
        """Handle shutdown signals"""
        sig_name = signal.Signals(signum).name
        logger.info(f"Received signal {sig_name}")
        self.cleanup()
        sys.exit(0)

    def serve_forever(self) -> None:
        """Start the server with signal handling"""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        # Start the server
        self.httpd = make_server("", self.port, self.app)
        logger.info(f"Serving on port {self.port}...")
        try:
            self.httpd.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.cleanup()
            sys.exit(1)


class BaseGeoLookup:
    def __init__(self, server: MMDBServer):
        self.server = server

    def process_georesult(
        self, georesult: GeoResult, mmdb: MMDBMeta, ip: str
    ) -> Dict[str, Any]:
        """Process georesult based on database type"""
        result: Dict[str, Any] = {
            "meta": {
                "description": mmdb["description"],
                "build_db": mmdb["build_db"],
                "db_source": mmdb["db_source"],
                "nb_nodes": mmdb["nb_nodes"],
            },
            "ip": ip,
        }

        # Copy all fields from georesult
        result.update(georesult)

        # Add country info if available
        if "country" in georesult and "iso_code" in georesult["country"]:
            result["country_info"] = self.server.country_lookup(
                country=georesult["country"]["iso_code"]
            )
        else:
            result["country_info"] = {}

        return result

    def lookup_ip(self, ip: str) -> List[Dict[str, Any]]:
        """Common IP lookup logic"""
        ret: List[Dict[str, Any]] = []
        for mmdb in self.server.mmdbs:
            try:
                georesult = mmdb["reader"].get(ip)
                if georesult is None:
                    continue

                processed_result = self.process_georesult(georesult, mmdb, ip)
                ret.append(processed_result)
            except Exception as e:
                logger.error(f"Error processing result from {mmdb['db_source']}: {e}")
                continue
        return ret


class GeoLookup(BaseGeoLookup):
    def on_get(self, req: Request, resp: Response, value: str) -> None:
        if not self.server.valid_ip_address(value):
            resp.status = falcon.HTTP_422
            resp.media = (
                "IPv4 or IPv6 address is in an incorrect format."
                "Dotted decimal for IPv4 or textual representation for IPv6 are required."  # noqa: E501
            )
            return

        ua = req.get_header("User-Agent")  # type: ignore
        ips = req.access_route  # type: ignore
        self.server.pub_lookup(value=f"{value} via {ips} using {ua}")

        resp.media = self.lookup_ip(value)
        return


class MyGeoLookup(BaseGeoLookup):
    def on_get(self, req: Request, resp: Response) -> None:
        ips: List[str] = list(req.access_route)  # type: ignore
        if ips:
            resp.media = self.lookup_ip(ips[0])
        return


def main() -> None:
    server = MMDBServer()
    server.serve_forever()


if __name__ == "__main__":
    main()
