# mmdb-server

This is a fork of [mmdb-server](https://github.com/adulau/mmdb-server) with optimized Docker support. The original project is by Alexandre Dulaunoy.

## Changes in this fork

- Optimized Docker image size (reduced from ~300MB to ~100MB)
- Multi-stage build process
- Support for volume mounting of database files
- Non-root container execution (using distroless base image)
- Integration with MMDB format databases
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

```json
[
  {
    "country": {
      "iso_code": "BE"
    },
    "meta": {
      "description": {
        "en": "GeoLite2 Country database"
      },
      "build_db": "2024-03-19 17:23:15",
      "db_source": "GeoLite2-Country",
      "nb_nodes": 1159974
    },
    "ip": "188.65.220.25",
    "country_info": {
      "Country": "Belgium",
      "Alpha-2 code": "BE",
      "Alpha-3 code": "BEL",
      "Numeric code": "56",
      "Latitude (average)": "50.8333",
      "Longitude (average)": "4"
    }
  }
]
```

# Output format

The output format is an array of JSON objects (to support multiple geo location databases). Each JSON object includes:
- `meta`: Information about the database source and build time
- `country`: Geographic location and ASN information of the queried IP address
- `ip`: The queried IP address
- `country_info`: Additional country information (codes, coordinates)

# API Documentation

The API is documented using the OpenAPI 3.1 specification. You can find the complete API documentation in the `openapi.yaml` file. This specification includes:
- Detailed endpoint descriptions
- Request/response schemas
- Example requests and responses
- Error handling documentation

You can use this specification with tools like Swagger UI, Postman, or any OpenAPI-compatible tool to:
- Explore the API interactively
- Generate client libraries in various programming languages
- Test the API endpoints
- Understand the response formats

# Public online version of the original mmdb-server implementation by Alexandre Dulaunoy

- [https://ip.circl.lu/](https://ip.circl.lu/) - lookup via [https://ip.circl.lu/geolookup/8.8.8.8](https://ip.circl.lu/geolookup/8.8.8.8)
- [https://ipv4.circl.lu](https://ipv4.circl.lu/) If you are dual-homed IPv6/IPv4, return your IPv4 address. 
- [https://ipv6.circl.lu](https://ipv6.circl.lu/) If you are dual-homed IPv6/IPv4, return your IPv6 address.

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