# mmdb-server

This is a fork of [mmdb-server](https://github.com/adulau/mmdb-server) with optimized Docker support. The original project is by Alexandre Dulaunoy.

## Important Note About Database Format

This server is specifically designed to work with MaxMind's GeoIP2/GeoLite2 database format. While it can technically work with any MMDB format file, the response structure is tightly coupled to MaxMind's data structure, including:
- GeoLite2-ASN (for AS number and organization)
- GeoLite2-City (for city-level geolocation)
- GeoLite2-Country (for country-level geolocation)

The server will preserve MaxMind's original data structure and add some custom fields:
- `meta`: Server metadata about the database
- `ip`: The queried IP address
- `country_info`: Additional country information from a separate source

## Changes in this fork

- Optimized Docker image size (reduced from ~300MB to ~100MB)
- Multi-stage build process
- Support for volume mounting of database files
- Non-root container execution (using distroless base image)
- Integration with MMDB format databases
- Graceful shutdown
- Example docker-compose.yml provided for easy deployment

mmdb-server is an open source fast API server to lookup IP addresses for their geographic location, AS number. The server can be used with any [MaxMind DB File Format](https://maxmind.github.io/MaxMind-DB/) or file in the same format.

mmdb-server includes a free and open [GeoOpen-Country database](https://data.public.lu/fr/datasets/geo-open-ip-address-geolocation-per-country-in-mmdb-format/) for IPv4 and IPv6 addresses. The file [GeoOpen-Country](https://cra.circl.lu/opendata/geo-open/mmdb-country/) and [GeoOpen-Country-ASN](https://cra.circl.lu/opendata/geo-open/mmdb-country-asn/) are generated on a regular basis from AS announces and their respective whois records.

# Installation

## Classic

Python 3.10+ is required to run the mmdb-server with poetry.

- `curl -sSL https://install.python-poetry.org | python3 -`
- Log out and Log in again
- `poetry install`
- `cp ./etc/server.conf.sample ./etc/server.conf`
- `poetry run serve`

## Docker

The server can use any database in the MMDB format. Here's how to run it:

### Setup with Docker Compose and MaxMind's GeoIP Lite DB

1. Sign up for a free MaxMind account at https://www.maxmind.com/en/geolite2/signup (if you want to use MaxMind's GeoLite2 databases)
2. Get your Account ID and License Key from your MaxMind account
3. Copy the environment template:
   ```bash
   cp .env.geoip-updater.dist .env.geoip-updater
   ```
4. Edit `.env.geoip-updater` with your MaxMind credentials:
   ```
   GEOIPUPDATE_ACCOUNT_ID=YOUR_ACCOUNT_ID
   GEOIPUPDATE_LICENSE_KEY=YOUR_LICENSE_KEY
   GEOIPUPDATE_EDITION_IDS=GeoLite2-ASN GeoLite2-City GeoLite2-Country
   ```
5. Start the services:
   ```bash
   docker compose up -d
   ```

This setup includes:
- A GeoIP updater service that automatically downloads and updates databases daily (if using MaxMind)
- The mmdb-server service using the shared databases

# Usage

## Lookup of an IP address

`curl -s http://127.0.0.1:8000/geolookup/188.65.220.25 | jq .`

# Output format

The output format is an array of JSON objects (to support multiple geo location databases). The structure of each object depends on the MaxMind database type being used:

**For GeoLite2-ASN database:**
```json
{
  "autonomous_system_number": 15169,
  "autonomous_system_organization": "Google LLC",
  "ip": "8.8.8.8",
  "meta": {
    "description": {"en": "GeoLite2-ASN database"},
    "build_db": "2024-03-19 17:23:15",
    "db_source": "GeoLite2-ASN",
    "nb_nodes": 1159974
  }
}
```

**For GeoLite2-Country/City databases:**
```json
{
  "continent": {
    "code": "NA",
    "geoname_id": 6255149,
    "names": {"en": "North America", "es": "Norteamérica", ...}
  },
  "country": {
    "geoname_id": 6252001,
    "iso_code": "US",
    "names": {"en": "United States", "es": "Estados Unidos", ...}
  },
  "location": {  // Only in City database
    "accuracy_radius": 1000,
    "latitude": 37.751,
    "longitude": -97.822,
    "time_zone": "America/Chicago"
  },
  "ip": "8.8.8.8",
  "meta": {
    "description": {"en": "GeoLite2-City database"},
    "build_db": "2024-03-19 17:23:15",
    "db_source": "GeoLite2-City",
    "nb_nodes": 1159974
  },
  "country_info": {
    "Country": "United States",
    "Alpha-2 code": "US",
    "Alpha-3 code": "USA",
    "Numeric code": "840",
    "Latitude (average)": "38",
    "Longitude (average)": "-97"
  }
}
```

Note: The exact fields available depend on the MaxMind database being used. The server adds the `meta`, `ip`, and `country_info` fields to MaxMind's original structure.

# API Endpoints

The server provides two main endpoints:

## GET /geolookup/{ip}
Look up information for a specific IP address.
- Parameter: `ip` (IPv4 or IPv6 address)
- Example: `curl -s http://127.0.0.1:8000/geolookup/8.8.8.8 | jq .`

## GET /
Look up information for the requesting client's IP address.
- Example: `curl -s http://127.0.0.1:8000/ | jq .`

For detailed information about the fields returned by each database type, please refer to MaxMind's official documentation:
- [GeoIP2 City/Country Database Fields](https://dev.maxmind.com/geoip/docs/databases/city-and-country?lang=en)
- [GeoIP2 ASN Database Fields](https://dev.maxmind.com/geoip/docs/databases/asn?lang=en)

# Source Code

Source code available at:
- This fork: [https://github.com/2snem6/mmdb-server](https://github.com/2snem6/mmdb-server)
- Original project: [https://github.com/adulau/mmdb-server](https://github.com/adulau/mmdb-server)

# License

This program is a modified version of mmdb-server, originally created by Alexandre Dulaunoy.
Both the original work and this modified version are licensed under the GNU Affero General Public License version 3.

```
    Copyright (C) 2022-2024 Alexandre Dulaunoy
    Copyright (C) 2025 Daniel Limia (daniel@hireflix.com) (Docker optimizations)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
```