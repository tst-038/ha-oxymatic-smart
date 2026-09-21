<p align="center">
  <img src="https://raw.githubusercontent.com/tst-038/ha-oxymatic-smart/main/images/logo.png" alt="OxyMatic Smart Logo" width="480">
</p>

<h1 align="center">OxyMatic Smart for Home Assistant</h1>

<p align="center">
  A modern, rock-solid Home Assistant custom integration for <b>Hydrover OxyMatic® Smart</b> automated pool water disinfection systems (ABOT - Advanced Bipolar Oxidation Technology).
</p>

<p align="center">
  <a href="https://github.com/hacs/default"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS"></a>
  <a href="https://github.com/tst-038/ha-oxymatic-smart/releases"><img src="https://img.shields.io/badge/version-1.0.0-blue.svg?style=for-the-badge" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge" alt="License"></a>
</p>

---

## 🌟 Highlights

* **Complete Pool Chemistry Monitoring**: Live tracking of **pH**, **ORP / Redox (mV)**, and **Water Temperature**.
* **ABOT Disinfection Telemetry**: Live **$O_2$ Hydrolysis** current & voltage, and **Copper Ionization** current & voltage.
* **Full Relay & Equipment Control**:
  * 🔄 **Filtration Pump** switch & running status
  * 🔥 **Heater Relay** switch & heating demand status
  * 💡 **Pool Lights** toggle
  * 🌊 **Water Flow Detector** binary sensor
  * 🔀 **Auxiliary 1** & **Auxiliary 2** relay switches
* **Built for 24/7 Stability**:
  * 🛡️ **Transparent Session Renewal**: Automatically handles ASP.NET session cookie expiration without dropping connection or requiring manual re-auth.
  * ⏱️ **Network Hiccup Shield**: Retains last known state through brief 502/503 server or network glitches (3-minute grace period) to eliminate dashboard entity flapping.
  * 🚨 **Accurate Physical Offline Detection**: Instantly marks entities `unavailable` when the physical pool controller disconnects, so you never see stale readings when the unit is off.
  * ⚡ **Rate-Limiting Protection**: Caches device identifiers across polling cycles to minimize redundant cloud requests.

---

## 📦 Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Enter the repository URL:
   ```text
   https://github.com/tst-038/ha-oxymatic-smart
   ```
4. Select Category: **Integration** and click **Add**.
5. Find **OxyMatic Smart Pool** in the HACS store and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release `.zip` or clone this repository.
2. Copy the `custom_components/oxymatic` directory into your Home Assistant `<config>/custom_components/` directory:
   ```text
   config/
   └── custom_components/
       └── oxymatic/
           ├── __init__.py
           ├── binary_sensor.py
           ├── config_flow.py
           ├── const.py
           ├── coordinator.py
           ├── entity.py
           ├── light.py
           ├── manifest.json
           ├── oxymatic.py
           ├── sensor.py
           ├── strings.json
           ├── switch.py
           └── translations/
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, navigate to **Settings** $\rightarrow$ **Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **OxyMatic Smart Pool**.
4. Enter your OxyMatic cloud credentials:
   * **Username**: Your Hydrover account username
   * **Password**: Your Hydrover account password
5. Submit. Your OxyMatic controller will be automatically discovered with all associated sensors, switches, and diagnostic entities!

---

## 📊 Exposed Entities

| Domain | Entity | Description |
| :--- | :--- | :--- |
| `sensor` | `water_temperature` | Pool water temperature (°C) |
| `sensor` | `ph` | Pool water pH value |
| `sensor` | `orp_redox` | Redox potential (mV) |
| `sensor` | `o2_current` | Hydrolysis $O_2$ current (A) |
| `sensor` | `o2_voltage` | Hydrolysis $O_2$ voltage (V) |
| `sensor` | `ion_current` | Ionization copper current (mA) |
| `sensor` | `ion_voltage` | Ionization copper voltage (V) |
| `sensor` | `target_water_temperature` | Target pool setpoint temperature (°C) |
| `sensor` | `active_program` | Controller active program |
| `sensor` | `operating_mode` | System operating mode (Auto, Manual, etc.) |
| `sensor` | `last_read` | Last successful sync timestamp |
| `sensor` | `status_message` | Controller status notification |
| `switch` | `filtration_pump` | Filtration pump control relay |
| `switch` | `pool_heater` | Pool heating demand relay |
| `switch` | `aux1` | Auxiliary relay 1 |
| `switch` | `aux2` | Auxiliary relay 2 |
| `light` | `pool_lights` | Underwater pool lighting |
| `binary_sensor` | `cloud_connection` | Connectivity to Hydrover cloud & controller |
| `binary_sensor` | `pump_running` | Filtration pump running state |
| `binary_sensor` | `heating_active` | Heating demand active state |
| `binary_sensor` | `water_flow` | Flow switch detection |
| `binary_sensor` | `oxidation_active` | $O_2$ oxidation running |
| `binary_sensor` | `ionization_active` | Copper ionization running |

---

## 🔒 Privacy, Security & SSL Notice

* **Credential Storage**: Your credentials are stored strictly within Home Assistant's local encrypted storage and are never transmitted anywhere except directly to Hydrover.
* **HTTPS & SSL Certificate Note**: Communication with the official Hydrover OxyMatic cloud portal (`oxymaticapp.hydrover.eu`) is performed over HTTPS. However, because Hydrover's cloud server SSL certificate is currently expired on their hosting end, TLS certificate verification is disabled (`verify=False`) in the client to allow communication with the portal.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
