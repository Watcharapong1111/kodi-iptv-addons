# coding=utf-8
#
#      Copyright (C) 2018 Dmitry Vinogradov
#      https://github.com/kodi-iptv-addons
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA  02110-1301, USA.
#

from iptvlib.api import Api, ApiException
from iptvlib.models import *


class Stalker(Api):
    mac = None  # type: str
    timezone = None  # type: str
    hostname = None  # type: str
    use_origin_icons = None  # type: bool
    adult = None  # type: bool
    timeshift = None  # type: int
    _open_epg_cids = None  # type: list[str]

    def __init__(self, mac, timezone, hostname, timeshift, adult, **kwargs):
        super(Stalker, self).__init__(**kwargs)
        self.mac = mac
        self.timezone = timezone
        self.hostname = hostname
        self.timeshift = timeshift
        self.adult = adult
        Model.API = self

    @property
    def user_agent(self):
        return "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) " \
               "MAG200 stbapp ver: 2 rev: 250 Safari/533.3 "

    @property
    def base_api_url(self):
        return "http://%s/stalker_portal/%%s" % self.host

    @property
    def base_icon_url(self):
        return "http://%s/stalker_portal/misc/logos/320/%%s" % self.host

    @property
    def host(self):
        return self.hostname

    @property
    def diff_live_archive(self):
        return TENSECS

    @property
    def archive_ttl(self):
        return TREEDAYS

    def get_cookie(self):
        return ""

    def default_headers(self, headers=None, force_login=True):
        headers = headers or {}
        token = self.read_cookie_file()
        if token == "" and force_login is True:
            self.login()
            return self.default_headers(headers)
        if token:
            headers["Authorization"] = token
        headers["Accept"] = "*/*"
        headers["Referer"] = "http://%s/stalker_portal/c/"
        headers["Accept-Charset"] = "UTF-8,*;q=0.8."
        headers["Cookie"] = "mac=%s; stb_lang=en; timezone=%s" % (self.mac, self.timezone)
        return headers

    def is_login_request(self, uri, payload=None, method=None, headers=None):
        return "auth/token.php" in uri

    def login(self):
        self.handshake()
        profile = self.get_profile()
        status = int(profile.get("status", 1))
        if status == 2:
            if not self.do_auth():
                raise ApiException("Authorization failed", Api.E_API_ERROR)
            profile.update(self.get_profile(1))
            self.auth_status = self.AUTH_STATUS_OK
        elif status == 0:
            self.auth_status = self.AUTH_STATUS_OK
        else:
            raise ApiException("Authorization failed", Api.E_API_ERROR)

        self.write_settings_file(profile)

    def handshake(self):
        # type: () -> str
        self.write_cookie_file("")
        payload = {
            "type": "stb",
            "action": "handshake"
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers(force_login=False))
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        token = response["js"]["token"]
        self.write_cookie_file("Bearer %s" % (token,))
        return token

    def get_profile(self, auth_second_step=0):
        # type: (int) -> dict
        payload = {
            "type": "stb",
            "action": "get_profile",
            "stb_type": "MAG250",
            "sn": "0000000000000",
            "ver": "ImageDescription: 0.2.16-250; "
                   "ImageDate: 18 Mar 2013 19:56:53 GMT+0200; "
                   "PORTAL version: 4.9.9; "
                   "API Version: JS API version: 328; "
                   "STB API version: 134; "
                   "Player Engine version: 0x566",
            "not_valid_token": 0,
            "auth_second_step": auth_second_step,
            "hd": 1,
            "num_banks": 1,
            "image_version": 216,
            "hw_version": "1.7-BD-00"
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers(force_login=False))
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        return response["js"]

    def do_auth(self):
        # type: () -> bool
        payload = {
            "type": "stb",
            "action": "do_auth",
            "login": self.username,
            "password": self.password
        }
        request = self.prepare_request("server/load.php", payload, "POST",
                                       headers=self.default_headers(force_login=False))
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        return response["js"]

    def get_genres(self):
        payload = {
            "type": "itv",
            "action": "get_genres",
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers())
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        if "js" not in response:
            raise ApiException(response, Api.E_API_ERROR)
        return response["js"]

    def get_channels(self):
        # type: () -> list
        payload = {
            "type": "itv",
            "action": "get_all_channels",
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers())
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        if "js" not in response:
            raise ApiException(response, Api.E_API_ERROR)
        return response["js"]["data"]

    def get_epg_info(self):
        payload = {
            "type": "epg",
            "action": "get_simple_data_table",
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers())
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        if "js" not in response:
            raise ApiException(response, Api.E_API_ERROR)
        return response["js"]["data"]

    def create_link(self, cmd):
        payload = {
            "type": "itv",
            "action": "create_link",
            "cmd": cmd
        }
        request = self.prepare_request("server/load.php", payload, headers=self.default_headers())
        response = self.send_request(request)
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))
        if "js" not in response:
            raise ApiException(response, Api.E_API_ERROR)
        url = response["js"]["cmd"]
        return url.replace("ffmpeg ", "").split()[0]



    def get_groups(self):
        groups = OrderedDict()
        for group_data in self.get_genres():
            if all(k in group_data for k in ("id", "title", "censored", "number")) is False:
                continue
            groups[str(group_data["id"])] = Group(
                str(group_data["id"]),
                group_data["title"],
                OrderedDict(),
                int(group_data["number"])
            )

        channels = self.get_channels()
        for channel_data in channels:
            if self.adult is False and bool(int(channel_data.get("censored", 0))) is True:
                continue
            channel = Channel(
                cid=str(channel_data["id"]),
                gid=str(channel_data["tv_genre_id"]),
                name=channel_data["name"],
                icon=self.base_icon_url % channel_data["logo"],
                epg=True,
                archive=bool(channel_data.get("archive", 0)),
                protected=bool(channel_data.get("censored", False)),
                url=channel_data["cmd"]
            )
            groups[channel.gid].channels[channel.cid] = channel
        return groups

    def get_stream_url(self, cid, ut_start=None):
        channel = self.channels[cid]
        if ut_start is None:
            return self.create_link(channel.url)

        ut_start = int(ut_start) - (HOUR * self.timeshift)
        program = None  # type: Program

        for p in channel.programs.values():  # type: Program
            if p.ut_start <= ut_start < p.ut_end:
                program = p
                break

        if program is not None:
            uri = "api/api_v2.php?_resource=users/%s/epg/%s/link" % \
                  (self.read_settings_file().get("user_id"), program.id)
            response = self.make_request(uri, headers=self.default_headers())
            if response.get("status") == "OK":
                return response.get("results")

        raise ApiException(get_string(TEXT_NOT_PLAYABLE_ID), Api.E_UNKNOW_ERROR)

    def get_epg(self, cid):
        settings = self.read_settings_file()
        if not settings:
            self.login()
            return self.get_channels()
        start = int(time_now() - self.archive_ttl)
        end = int(time_now() + (DAY * 2))
        uri = "api/api_v2.php?_resource=users/%s/tv-channels/%s/epg&from=%s&to=%s" % \
              (settings.get("user_id"), cid, start, end)
        response = self.make_request(uri, headers=self.default_headers())
        is_error, error = Api.is_error_response(response)
        if is_error:
            raise ApiException(error.get("message"), error.get("code"))

        programs = OrderedDict()
        prev = None  # type: Program
        for entry in response.get("results", []):
            program = Program(
                cid,
                self.channels[cid].gid,
                entry["start"],
                entry["end"],
                entry["name"],
                "",
                bool(entry["in_archive"])
            )
            program.data["id"] = entry["id"]
            if prev is not None:
                program.prev_program = prev
                prev.next_program = program
            programs[program.ut_start] = prev = program
        return programs
