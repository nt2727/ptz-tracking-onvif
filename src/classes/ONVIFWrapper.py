# -*- coding: utf-8 -*-
"""
ONVIFWrapper
============
NovaVision `bootstrap()` aşamasında bir kez oluşturulur ve process ömrü boyunca
memory'de tutulur (rapor md. 3.2 - Camera Connection Pool / State Management).

Kamera ile tüm SOAP iletişimi ayrı bir arka plan thread'inde çalışan kendi
asyncio event loop'u üzerinden yürütülür (rapor md. 2.2 - Asynchronous Structure).
`continuous_move` / `go_to_preset` gibi metodlar bu yüzden senkron (bloklamayan)
görünür: komutu `asyncio.run_coroutine_threadsafe` ile arka plan loop'una atar
ve hemen döner - ana video işleme pipeline'ı asla ONVIF ağ gecikmesiyle bloklanmaz.

Kütüphane: onvif-zeep-async (Roboflow'un onvif-zeep-f'i ile aynı API yüzeyi:
ONVIFCamera, await cam.update_xaddrs(), await cam.create_ptz_service() vb.)
"""

import asyncio
import threading
import time
from typing import Optional, Dict

from onvif import ONVIFCamera
from onvif.util import discover  # WS-Discovery için import

from sdks.novavision.src.base.logger import LoggerManager

logger = LoggerManager()


def _now_ms() -> int:
    return int(round(time.time() * 1000))


class VelocityLimits:
    """Kameranın ContinuousMove için desteklediği gerçek min/max hız aralığı."""

    def __init__(self, pan_tilt_space, zoom_space):
        self.x_min, self.x_max = pan_tilt_space.XRange.Min, pan_tilt_space.XRange.Max
        self.y_min, self.y_max = pan_tilt_space.YRange.Min, pan_tilt_space.YRange.Max
        if zoom_space is not None:
            self.z_min, self.z_max = zoom_space.XRange.Min, zoom_space.XRange.Max
        else:
            self.z_min, self.z_max = 0.0, 0.0

    def scale_x(self, v: float) -> float:
        return v * (abs(self.x_min) if v < 0 else abs(self.x_max))

    def scale_y(self, v: float) -> float:
        return v * (abs(self.y_min) if v < 0 else abs(self.y_max))

    def scale_z(self, v: float) -> float:
        return v * (abs(self.z_min) if v < 0 else abs(self.z_max))


class ONVIFWrapper:
    """
    Tek bir ONVIF kamerayla olan tüm bağlantı durumunu (servisler, profil token'ı,
    hız limitleri, preset'ler) ve son komut zaman damgasını (rate limiting için)
    tutan sınıf.
    """

    def __init__(self, ip: str, port: int, username: str, password: str):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None

        self.camera: Optional[ONVIFCamera] = None
        self._ptz = None
        self._media_profile_token: Optional[str] = None
        self._velocity_limits: Optional[VelocityLimits] = None
        self._presets: Dict[str, object] = {}

        self._connected = False
        self._connect_error: Optional[str] = None

        self._last_update_ms: Optional[int] = None
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_z = 0.0

        # simulate_variable_speed sayaçları (rapor md. 2.2)
        self._sim_count_x = 0
        self._sim_count_y = 0
        self._sim_count_z = 0

        self._seeking = False

    # ------------------------------------------------------------------
    # Bağlantı / bootstrap
    # ------------------------------------------------------------------

    def start_background_loop(self):
        """
        bootstrap() içinde çağrılır. Kendi asyncio event loop'unu ayrı bir
        daemon thread'de başlatır ve kamera bağlantısını o loop üzerine
        planlar (fire-and-forget - bootstrap'ı bloklamamak için beklemiyoruz,
        bağlantı hazır olana kadar continuous_move no-op döner).
        """
        self.loop = asyncio.new_event_loop()

        def _run():
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.thread = threading.Thread(target=_run, daemon=True)
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self._connect_async(), self.loop)

    def _schedule(self, coro):
        if self.loop is None:
            return None
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def _connect_async(self):
        try:
            self.camera = ONVIFCamera(self.ip, self.port, self.username, self.password)
            await self.camera.update_xaddrs()

            media = await self.camera.create_media_service()
            profiles = await media.GetProfiles()
            media_profile = profiles[0]
            self._media_profile_token = media_profile.token

            self._ptz = await self.camera.create_ptz_service()

            config_request = self._ptz.create_type("GetConfigurationOptions")
            config_request.ConfigurationToken = media_profile.PTZConfiguration.token
            config_options = await self._ptz.GetConfigurationOptions(config_request)

            pan_tilt_space = None
            if hasattr(config_options.Spaces, "ContinuousPanTiltVelocitySpace"):
                spaces = config_options.Spaces.ContinuousPanTiltVelocitySpace
                if spaces:
                    pan_tilt_space = spaces[0]
            if pan_tilt_space is None:
                raise ValueError("Kamera ContinuousPanTiltVelocitySpace desteklemiyor")

            zoom_space = None
            if hasattr(config_options.Spaces, "ContinuousZoomVelocitySpace"):
                spaces = config_options.Spaces.ContinuousZoomVelocitySpace
                if spaces:
                    zoom_space = spaces[0]

            self._velocity_limits = VelocityLimits(pan_tilt_space, zoom_space)

            try:
                presets = await self._ptz.GetPresets({"ProfileToken": self._media_profile_token})
                self._presets = {p["Name"]: p for p in presets}
            except Exception as e:
                logger.warning(f"ONVIFWrapper - preset listesi alınamadı: {e}")
                self._presets = {}

            self._connected = True
            self._connect_error = None
            logger.info(f"ONVIFWrapper - kameraya bağlanıldı: {self.ip}:{self.port}")

        except Exception as e:
            self._connected = False
            self._connect_error = str(e)
            logger.error(f"ONVIFWrapper - bağlantı hatası ({self.ip}:{self.port}): {e}")

    def is_connected(self) -> bool:
        return self._connected

    def connection_error(self) -> Optional[str]:
        return self._connect_error

    def seeking(self) -> bool:
        return self._seeking

    # ------------------------------------------------------------------
    # Rate limiting / simulate_variable_speed yardımcıları
    # ------------------------------------------------------------------

    def _can_send(self, rate_limit_ms: int) -> bool:
        return self._last_update_ms is None or (_now_ms() - self._last_update_ms) >= rate_limit_ms

    @staticmethod
    def _simulate_speed(speed: float, count: int, can_update: bool):
        """
        Değişken hız desteklemeyen kameralar için: %speed kadar süre max hızda
        hareket ettirip sonra durdurma komutu göndererek ortalama hızı simüle
        eder (rapor md. 2.2).
        """
        count += 1
        if speed != 0 and count >= max(1, int(round(1.0 / abs(speed)))):
            speed = 1.0 if speed > 0 else -1.0
            if can_update:
                count = 0
        else:
            speed = 0.0
        return speed, count

    # ------------------------------------------------------------------
    # Hareket komutları
    # ------------------------------------------------------------------

    def continuous_move(
            self,
            x: float,
            y: float,
            z: float = 0.0,
            rate_limit_ms: int = 250,
            simulate_variable_speed: bool = False,
    ):
        """
        x, y, z: -1..1 aralığında normalize hız komutları.
        Thread-safe, non-blocking - komutu arka plan loop'una atar ve döner.
        """
        if not self._connected or self._ptz is None:
            return

        can_update = self._can_send(rate_limit_ms)

        if simulate_variable_speed:
            x, self._sim_count_x = self._simulate_speed(x, self._sim_count_x, can_update)
            y, self._sim_count_y = self._simulate_speed(y, self._sim_count_y, can_update)
            z, self._sim_count_z = self._simulate_speed(z, self._sim_count_z, can_update)

        # dur komutlarını rate limit'ten muaf tutuyoruz: hunting'i önlemek için
        # "dur" her zaman hemen gitmeli, aksi halde obje dead zone'a girdiğinde
        # kamera rate_limit_ms kadar daha hareket etmeye devam eder.
        stopping = (x == 0 and self._last_x != 0) or (y == 0 and self._last_y != 0) or (z == 0 and self._last_z != 0)

        if not stopping and not can_update:
            return

        self._last_x, self._last_y, self._last_z = x, y, z
        self._schedule(self._continuous_move_async(x, y, z))
        self._last_update_ms = _now_ms()
        self._seeking = bool(x != 0 or y != 0 or z != 0)

    async def _continuous_move_async(self, x: float, y: float, z: float):
        try:
            limits = self._velocity_limits
            request = self._ptz.create_type("ContinuousMove")
            request.ProfileToken = self._media_profile_token
            request.Velocity = {
                "PanTilt": {"x": limits.scale_x(x), "y": limits.scale_y(y)},
                "Zoom": {"x": limits.scale_z(z)},
            }
            await self._ptz.ContinuousMove(request)
        except Exception as e:
            logger.error(f"ONVIFWrapper - ContinuousMove hatası: {e}")

    def stop(self):
        """Anlık dur komutu - rate limit'e tabi değil."""
        self.continuous_move(0, 0, 0, rate_limit_ms=0)

    def go_to_preset(self, preset_name: str):
        if not self._connected or self._ptz is None:
            return
        self._schedule(self._go_to_preset_async(preset_name))
        self._seeking = True

    async def _go_to_preset_async(self, preset_name: str):
        try:
            preset = self._presets.get(preset_name)
            if not preset:
                logger.error(
                    f"ONVIFWrapper - '{preset_name}' preset'i kamerada yok. "
                    f"Mevcut preset'ler: {list(self._presets.keys())}"
                )
                return
            request = self._ptz.create_type("GotoPreset")
            request.ProfileToken = self._media_profile_token
            request.PresetToken = preset["token"]
            request.Speed = {"PanTilt": {"x": 1.0, "y": 1.0}, "Zoom": {"x": 1.0}}
            await self._ptz.GotoPreset(request)
            self._seeking = False
        except Exception as e:
            logger.error(f"ONVIFWrapper - GotoPreset hatası: {e}")

    def close(self):
        try:
            self.stop()
            if self.loop is not None:
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception:
            pass

    # ==================================================================
    # YENİ EKLENEN METODLAR: WS-Discovery (Otomatik Kamera Bulma)
    # ==================================================================

    @staticmethod
    def discover_cameras(timeout: int = 5, username: str = "admin", password: str = "admin"):
        """
        Ağdaki tüm ONVIF uyumlu kameraları WS-Discovery ile tarar.
        Dönen liste: [('192.168.1.10', 80, [...]), ...] şeklindedir.
        """
        print("[ONVIF] Ağda ONVIF kamera aranıyor... (Bu işlem birkaç saniye sürebilir)")
        try:
            # WS-Discovery genellikle auth gerektirmez, ama parametre olarak tutuyoruz
            devices = discover(timeout=timeout)
            return devices
        except Exception as e:
            print(f"[ONVIF] WS-Discovery hatası: {e}")
            return []

    def connect_from_discovery(self, device_info, username: str = "admin", password: str = "admin"):
        """
        WS-Discovery'den gelen bilgilerle bağlantı kurar.
        Mevcut bağlantıyı sıfırlar ve yeni kimlik bilgileriyle bağlanır.
        """
        ip, port, _ = device_info
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password

        # Bağlantı durumunu sıfırla
        self._connected = False
        self._connect_error = None
        self.camera = None
        self._ptz = None
        self._media_profile_token = None
        self._velocity_limits = None
        self._presets = {}

        # Yeni bağlantıyı başlat
        self.start_background_loop()