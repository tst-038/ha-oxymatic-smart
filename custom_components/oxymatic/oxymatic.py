"""OxyMatic pool controller API client."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup, Tag

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://oxymaticapp.hydrover.eu"

KNOWN_MANUAL_PARAMS = {
    "oxy": "Oxygen/Ozone",
    "pump": "Filtration pump",
    "decal": "Decalcifier",
    "ionper": "Ionizer/Peroxide",
    "aux1": "Auxiliary 1",
    "light": "Lights (AUX3)",
    "aux2": "Auxiliary 2",
    "heat": "Heater / heat pump",
    "flow": "Varioflow",
}

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _to_float(val: str) -> float | None:
    """Parse European-formatted decimal to float."""
    if not val or val.strip() in ("", "-", "–"):
        return None
    try:
        return float(val.replace(",", ".").strip())
    except ValueError:
        return None


@dataclass
class DeviceStatus:
    """Parsed status of a single OxyMatic device."""

    device_id: int
    device_name: str = ""
    alias: str = ""

    # Header & connection
    mode: str = ""
    program: str = ""
    error_message: str = ""
    is_connected: bool = True

    # Output states (from PantallaMan and status page)
    pump_state: str = ""  # on / off
    heat_state: str = ""  # on / off
    lights_state: str = ""  # on / off
    lights_mode: str = ""  # manual / auto
    aux1_state: str = ""  # on / off
    aux1_mode: str = ""
    aux2_state: str = ""  # on / off
    aux2_mode: str = ""

    # Live button states mapping parameter -> is_active
    buttons: dict[str, bool] = field(default_factory=dict)

    # Readings
    water_temp: float | None = None
    water_temp_max: float | None = None

    oxy_current: float | None = None
    oxy_voltage: float | None = None
    ion_current: float | None = None
    ion_voltage: float | None = None

    ph: float | None = None
    ph_min: float | None = None
    ph_max: float | None = None

    orp: float | None = None  # Redox/Rx
    orp_min: float | None = None
    orp_max: float | None = None

    copper: float | None = None
    copper_min: float | None = None
    copper_max: float | None = None

    chlorine: float | None = None
    chlorine_min: float | None = None
    chlorine_max: float | None = None

    last_read: str = ""
    last_edit: str = ""

    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class DeviceInfo:
    """Basic device info from account page."""

    device_id: int
    alias: str = ""
    device_name: str = ""
    idn: str = ""
    serial: str = ""


@dataclass
class ChannelSchedule:
    """Timer schedule for one output channel (pid 0-4)."""

    channel_id: int
    days: list[dict[str, Any]] = field(default_factory=list)



class OxyMaticError(Exception):
    """Base exception for OxyMatic errors."""


class OxyMaticAuthError(OxyMaticError):
    """Invalid credentials provided."""


class OxyMaticConnectionError(OxyMaticError):
    """Network or server error communicating with OxyMatic."""


class OxyMaticClient:
    """Client for the OxyMatic pool controller web app."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        verify_ssl: bool = False,
        username: str = "",
        password: str = "",
    ) -> None:
        self._base = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.verify = verify_ssl
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self._username = username
        self._password = password
        self._csrf_token: str = ""
        self._devices: dict[int, DeviceInfo] = {}
        self._logged_in = False

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, username: str | None = None, password: str | None = None) -> bool:
        """Authenticate against the OxyMatic app."""
        if username is not None:
            self._username = username
        if password is not None:
            self._password = password

        if not self._username or not self._password:
            raise OxyMaticAuthError("Missing username or password")

        try:
            resp = self._session.post(
                urljoin(self._base, "/home/login"),
                data={"user": self._username, "password": self._password},
                allow_redirects=False,
                timeout=15,
            )
        except requests.RequestException as err:
            raise OxyMaticConnectionError(f"Network error during login: {err}") from err

        if resp.status_code in (500, 502, 503, 504):
            raise OxyMaticConnectionError(f"Server error {resp.status_code} during login")

        if resp.status_code not in (301, 302, 303, 307, 308):
            _LOGGER.error("Login failed: status %s", resp.status_code)
            self._logged_in = False
            return False

        redirect = resp.headers.get("Location", "")
        if "/Users/account" not in redirect:
            _LOGGER.error("Unexpected redirect: %s", redirect)
            self._logged_in = False
            return False

        try:
            self._session.get(urljoin(self._base, redirect), timeout=15)
            self._logged_in = True
            self._update_csrf()
        except requests.RequestException as err:
            _LOGGER.warning("Failed to follow login redirect or update CSRF: %s", err)
            self._logged_in = True

        return True

    def _update_csrf(self) -> None:
        try:
            resp = self._session.get(
                urljoin(self._base, "/Users/account"), timeout=15
            )
        except requests.RequestException:
            return

        match = re.search(
            r'__RequestVerificationToken[^v]*value="([^"]+)"', resp.text
        )
        if match:
            self._csrf_token = match.group(1)
        else:
            self._csrf_token = self._session.cookies.get(
                "__RequestVerificationToken", ""
            )

    # ------------------------------------------------------------------
    # HTTP helper with automatic session recovery
    # ------------------------------------------------------------------

    def _request(
        self, method: str, url: str, auto_reauth: bool = True, **kwargs
    ) -> requests.Response:
        """Perform an HTTP request with automatic re-authentication on session expiry."""
        kwargs.setdefault("timeout", 15)
        full_url = urljoin(self._base, url)
        try:
            resp = self._session.request(method, full_url, **kwargs)
        except requests.RequestException as err:
            raise OxyMaticConnectionError(f"HTTP request to {url} failed: {err}") from err

        if self._check_session_expired(resp):
            if auto_reauth and self._username and self._password:
                _LOGGER.info("OxyMatic session expired. Re-authenticating automatically...")
                if self.login():
                    try:
                        return self._session.request(method, full_url, **kwargs)
                    except requests.RequestException as err:
                        raise OxyMaticConnectionError(f"Retry request to {url} failed: {err}") from err
            self._logged_in = False

        return resp

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    def _check_session_expired(self, resp: requests.Response) -> bool:
        """Return True if the response was redirected to the login page."""
        if "/home/login" in resp.url:
            self._logged_in = False
            return True
        return False

    def get_devices(self) -> dict[int, DeviceInfo]:
        """Discover devices from the account page."""
        resp = self._request("GET", "/Users/account")
        if self._check_session_expired(resp) or resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        devices: dict[int, DeviceInfo] = {}

        for selector in soup.find_all(class_="accordion-selector"):
            main_id = selector.get("main-id", "")
            if not main_id or not main_id.isdigit():
                continue
            dev_id = int(main_id)
            info = DeviceInfo(device_id=dev_id)
            for part in selector.get_text(strip=True).split(","):
                if ":" in part:
                    key, _, val = part.partition(":")
                    key = key.strip().lower()
                    val = val.strip()
                    if key == "alias":
                        info.alias = val
                    elif key == "device":
                        info.device_name = val
                    elif key == "idn":
                        info.idn = val
                    elif key == "serial":
                        info.serial = val
            devices[dev_id] = info

        self._devices = devices
        return devices

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_device_status(self, device_id: int) -> DeviceStatus | None:
        """Fetch and parse live device status."""
        resp = self._request("GET", f"/devices/DeviceStatus?id={device_id}")
        if resp.status_code != 200 or self._check_session_expired(resp):
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        status = DeviceStatus(device_id=device_id)

        # --- Pool name / header ---
        header = soup.find(class_="statusresume")
        if header:
            two_col = header.find(class_="two-column")
            if two_col:
                span = two_col.find("span")
                if span:
                    status.device_name = span.get_text(strip=True)
            second_col = header.find(class_="second")
            if second_col:
                texts = list(dict.fromkeys(
                    p.get_text(strip=True)
                    for p in second_col.find_all("p")
                    if p.get_text(strip=True)
                ))
                status.error_message = " | ".join(texts) if texts else ""

        # --- First column: temp, lights, aux1, aux2, last read ---
        for box in soup.find_all("div", class_=re.compile(r"\bfirst-col\b")):
            title_el = box.find(class_="title")
            status_el = box.find(class_="status")
            desc_el = box.find(class_="description")
            big_el = box.find(class_="big-number")
            max_el = box.find(class_="max")

            title = title_el.get_text(strip=True).lower() if title_el else ""
            status_text = status_el.get_text(strip=True) if status_el else ""
            desc = desc_el.get_text(strip=True) if desc_el else ""
            big = big_el.get_text(strip=True) if big_el else ""

            if "water temp" in title:
                status.water_temp = _to_float(big)
                if max_el:
                    status.water_temp_max = _to_float(max_el.get_text(strip=True))
                status.program = status_text
            elif "lights" in title:
                status.lights_mode = status_text
                status.lights_state = desc
            elif "aux1" in title:
                status.aux1_mode = status_text
                status.aux1_state = desc
            elif "aux2" in title:
                status.aux2_mode = status_text
                status.aux2_state = desc
            elif "last read" in title:
                status.last_read = status_text
            elif "last edit" in title:
                status.last_edit = status_text

        # --- Second column: OXY, ION, pH, Rx, Cu, CL ---
        for box in soup.find_all("div", class_=re.compile(r"\bsecond-col\b")):
            classes = " ".join(box.get("class", []))

            big_nums = box.find_all(class_="big-number")
            nums = [n.get_text(strip=True) for n in big_nums]

            info_el = box.find(class_="additional-info-text")
            info_text = info_el.get_text(strip=True) if info_el else ""

            # Identify by CSS class
            if "oxy" in classes:
                if len(nums) >= 2:
                    status.oxy_current = _to_float(nums[0])
                    status.oxy_voltage = _to_float(nums[1])

            elif "ion" in classes:
                if len(nums) >= 2:
                    status.ion_current = _to_float(nums[0])
                    status.ion_voltage = _to_float(nums[1])

            elif "ph" not in classes and "ion" not in classes and "oxy" not in classes:
                # Either pH, Rx, Cu, or CL — identified by the button text
                button = box.find(class_="button-config")
                btn_text = button.get_text(strip=True).lower() if button else ""

                # pH and Rx have the big numbers directly
                if btn_text == "ph":
                    if nums:
                        status.ph = _to_float(nums[0])
                    self._parse_min_max(info_text, "ph", status)

                elif btn_text == "rx":
                    if nums:
                        status.orp = _to_float(nums[0])
                    self._parse_min_max(info_text, "rx", status)

                elif btn_text == "cu":
                    raw_val = nums[0] if nums else ""
                    status.copper = _to_float(raw_val)
                    self._parse_min_max(info_text, "cu", status)

                elif btn_text == "cl":
                    raw_val = nums[0] if nums else ""
                    status.chlorine = _to_float(raw_val)
                    self._parse_min_max(info_text, "cl", status)

        # Check connection health from error message
        if status.error_message:
            msg = status.error_message.lower()
            if "connection error" in msg or "check device connection" in msg:
                status.is_connected = False
            else:
                status.is_connected = True
        else:
            status.is_connected = True

        # Enrich with live outputs from PantallaMan
        try:
            r_man = self._request("GET", f"/devices/PantallaMan?id={device_id}")
            if r_man.status_code == 200 and not self._check_session_expired(r_man):
                s_man = BeautifulSoup(r_man.text, "html.parser")
                for b in s_man.find_all("button", class_="manual-button"):
                    par = b.get("data-par")
                    if par:
                        classes = b.get("class", [])
                        is_on = "displayverde" in classes
                        status.buttons[par] = is_on

                if "pump" in status.buttons:
                    status.pump_state = "on" if status.buttons["pump"] else "off"
                if "heat" in status.buttons:
                    status.heat_state = "on" if status.buttons["heat"] else "off"
                if "aux1" in status.buttons and not status.aux1_state:
                    status.aux1_state = "on" if status.buttons["aux1"] else "off"
                if "aux2" in status.buttons and not status.aux2_state:
                    status.aux2_state = "on" if status.buttons["aux2"] else "off"
                if "light" in status.buttons and not status.lights_state:
                    status.lights_state = "on" if status.buttons["light"] else "off"
        except Exception as err:
            _LOGGER.debug("Failed to fetch PantallaMan: %s", err)

        return status

    def _parse_min_max(self, info_text: str, sensor: str, status: DeviceStatus) -> None:
        """Parse min/max from info text like 'pHMin=7,1 pHMax=7,5'."""
        label_map = {
            "ph": ("pHMin", "pHMax"),
            "rx": ("RxMin", "RxMax"),
            "cu": ("CuMin", "CuMax"),
            "cl": ("CuMin", "CuMax"),
        }
        mn_label, mx_label = label_map[sensor]
        pattern = rf"{mn_label}=([\d,]+)\s*{mx_label}=([\d,]+)"
        m = re.search(pattern, info_text)
        if m:
            mn_val = _to_float(m.group(1))
            mx_val = _to_float(m.group(2))
            if sensor == "ph":
                status.ph_min = mn_val
                status.ph_max = mx_val
            elif sensor == "rx":
                status.orp_min = mn_val
                status.orp_max = mx_val
            elif sensor == "cu":
                status.copper_min = mn_val
                status.copper_max = mx_val
            elif sensor == "cl":
                status.chlorine_min = mn_val
                status.chlorine_max = mx_val

    # ------------------------------------------------------------------
    # Manual control
    # ------------------------------------------------------------------

    def toggle_manual(self, device_id: int, parameter: str) -> bool:
        """Toggle a manual output (on/off or auto<->manual)."""
        if parameter not in KNOWN_MANUAL_PARAMS:
            _LOGGER.warning("Unknown parameter: %s", parameter)

        resp = self._request(
            "GET",
            "/Devices/ChangeManSetting",
            params={"id": device_id, "par": parameter},
        )
        return resp.status_code == 200 and resp.text.strip() == "1"

    def toggle_light(self, device_id: int) -> bool:
        """Convenience: toggle lights."""
        return self.toggle_manual(device_id, "light")

    def toggle_pump(self, device_id: int) -> bool:
        """Convenience: toggle filtration pump."""
        return self.toggle_manual(device_id, "pump")

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def get_settings(self, device_id: int) -> dict[str, str]:
        """Read current settings from the settings form."""
        resp = self._request("GET", f"/devices/settings?id={device_id}")
        if resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        form = soup.find("form")
        if not form:
            return {}

        settings: dict[str, str] = {}
        for inp in form.find_all("input"):
            name = inp.get("name", "")
            if not name:
                continue
            typ = inp.get("type", "")
            if typ == "checkbox":
                settings[name] = "true" if inp.has_attr("checked") else ""
            elif typ == "hidden" and inp.get("value") == "value":
                pass  # ASP.NET checkbox auxiliary hidden
            else:
                settings[name] = inp.get("value", "")

        return settings

    def save_settings(self, device_id: int, data: dict[str, str]) -> bool:
        """Save settings to the device."""
        if "__RequestVerificationToken" not in data:
            data["__RequestVerificationToken"] = self._csrf_token
        if "Id" not in data:
            data["Id"] = str(device_id)

        resp = self._request(
            "POST",
            f"/devices/settings?id={device_id}",
            data=data,
        )
        return resp.status_code in (200, 301, 302)

    # ------------------------------------------------------------------
    # Programs
    # ------------------------------------------------------------------

    def get_programs_html(self, device_id: int) -> str:
        """Raw programs page HTML."""
        resp = self._request("GET", f"/devices/DevicePrograms?id={device_id}")
        return resp.text

    # ------------------------------------------------------------------
    # Channel schedules
    # ------------------------------------------------------------------

    def get_channel(self, device_id: int, channel_id: int) -> ChannelSchedule:
        """Fetch timer schedule for a channel (0-4)."""
        resp = self._request(
            "GET",
            f"/devices/DeviceChannel?id={device_id}&pid={channel_id}",
        )
        if resp.status_code != 200:
            return ChannelSchedule(channel_id=channel_id)

        soup = BeautifulSoup(resp.text, "html.parser")
        schedule = ChannelSchedule(channel_id=channel_id)
        prefix = f"channel_I{device_id}P{channel_id}"

        for day in range(7):
            day_data: dict[str, Any] = {"day": day, "active": False, "slots": []}

            active_inp = soup.find(
                "input", class_=re.compile(rf"{prefix}D{day}A\b")
            )
            if active_inp and active_inp.has_attr("checked"):
                day_data["active"] = True

            for slot in range(3):
                slot_data: dict[str, str] = {}
                for on_off, prefix_label in ((0, "start"), (1, "end")):
                    for hm, hm_label in (("H", "hour"), ("M", "minute")):
                        inp = soup.find(
                            "input",
                            class_=re.compile(
                                rf"{prefix}D{day}S{slot}P{on_off}{hm}\b"
                            ),
                        )
                        if inp:
                            slot_data[f"{prefix_label}_{hm_label}"] = inp.get(
                                "value", "00"
                            )
                if slot_data:
                    day_data["slots"].append(slot_data)

            schedule.days.append(day_data)

        return schedule

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session(self) -> requests.Session:
        """The underlying requests session."""
        return self._session

    @property
    def is_logged_in(self) -> bool:
        """Whether the session is still authenticated."""
        return self._logged_in

    @property
    def csrf_token(self) -> str:
        """Current anti-forgery token."""
        return self._csrf_token
