#!/usr/bin/env python3
"""BLE control for the NEEWER RGB62 backlight (macOS / Windows both supported).

The protocol (command construction) is shared. Only the BLE transport is
swapped per platform:

  - macOS : CoreBluetooth. NEEWER Control Center keeps holding its own
            connection, so this module "piggybacks" onto it and can coexist
            with the official app.
  - Windows : first try WinRT to find a NEEWER "already connected to this
            PC" and piggyback on it (this coexists even while the control
            app on the PC holds the connection; a connected unit stops BLE
            advertising, so it cannot be found by scanning).
            Falls back to bleak's advertisement scan if none is found.
  - other   : bleak (BlueZ) advertisement scan only.

Usage:
    python neewer_light.py on                  # power on (does not change settings)
    python neewer_light.py off                 # power off (does not change settings)
    python neewer_light.py cct 50 5600         # 50% brightness, 5600K (neutral GM)
    python neewer_light.py cct 50 5600 30      # with GM specified (0-100, 50=neutral)

Note: the cct command switches the light into CCT mode. If it was being used
in HSI (RGB color) mode, the color settings will be overwritten.
Protocol source: github.com/keefo/NeewerLite Docs/Neewer-Light-Protocol.md
"""
import sys

IS_MAC = sys.platform == "darwin"

NEEWER_SVC = "69400001-B5A3-F393-E0A9-E50E24DCCA99"


def _cmd(tag: int, payload: bytes) -> bytes:
    body = bytes([0x78, tag, len(payload)]) + payload
    return body + bytes([sum(body) & 0xFF])


class _LightMixin:
    """Transport-independent command API. send() is implemented by each backend."""

    def send(self, data: bytes) -> None:  # pragma: no cover - implemented per backend
        raise NotImplementedError

    def power(self, on: bool) -> None:
        """Power on/off. Brightness/color settings are preserved."""
        self.send(_cmd(0x81, bytes([0x01 if on else 0x02])))

    def set_cct(self, brightness: int, kelvin: int, gm: int = 50) -> None:
        """Set brightness (0-100%) and color temperature (K) in CCT mode."""
        brt = max(0, min(100, int(brightness)))
        cct = max(0, min(255, round(kelvin / 100)))
        gm = max(0, min(100, int(gm)))
        self.send(_cmd(0x87, bytes([brt, cct, gm, 0x00, 0x00])))

    def set_hsi(self, hue: int, saturation: int, intensity: int) -> None:
        """Set color in HSI mode (hue: 0-360 deg, sat/int: 0-100)."""
        hue = max(0, min(360, int(hue)))
        self.send(_cmd(0x86, bytes([hue & 0xFF, hue >> 8,
                                    max(0, min(100, int(saturation))),
                                    max(0, min(100, int(intensity)))])))


# ============================================================ macOS backend

if IS_MAC:
    import threading

    import CoreBluetooth
    import Foundation
    import libdispatch
    import objc

    class _Delegate(Foundation.NSObject):
        def init(self):
            self = objc.super(_Delegate, self).init()
            for name in ("ready", "connected", "svc_done", "chr_done", "wrote"):
                setattr(self, name, threading.Event())
            return self

        def centralManagerDidUpdateState_(self, c):
            if c.state() == 5:  # powered on
                self.ready.set()

        def centralManager_didConnectPeripheral_(self, c, p):
            self.connected.set()

        def peripheral_didDiscoverServices_(self, p, e):
            self.svc_done.set()

        def peripheral_didDiscoverCharacteristicsForService_error_(self, p, s, e):
            self.chr_done.set()

        def peripheral_didWriteValueForCharacteristic_error_(self, p, ch, e):
            if e:
                print("write error:", e, file=sys.stderr)
            self.wrote.set()

    class _MacNeewer(_LightMixin):
        """A handle to an already-connected (or advertising) NEEWER light."""

        def __init__(self, timeout: float = 15.0):
            self._d = _Delegate.alloc().init()
            queue = libdispatch.dispatch_queue_create(b"neewer-ble", None)
            self._mgr = CoreBluetooth.CBCentralManager.alloc(
            ).initWithDelegate_queue_(self._d, queue)
            if not self._d.ready.wait(timeout):
                raise RuntimeError("Bluetooth is not enabled")
            uuids = [CoreBluetooth.CBUUID.UUIDWithString_(NEEWER_SVC)]
            periphs = self._mgr.retrieveConnectedPeripheralsWithServices_(uuids)
            self._p = next((p for p in periphs
                            if "NEEWER" in str(p.name() or "").upper()), None)
            if self._p is None:
                raise RuntimeError(
                    "No connected NEEWER light found "
                    "(check the Control Center connection)")
            self._mgr.connectPeripheral_options_(self._p, None)
            if not self._d.connected.wait(timeout):
                raise RuntimeError("Timed out connecting to the light")
            self._p.setDelegate_(self._d)
            self._p.discoverServices_(None)
            self._d.svc_done.wait(timeout)
            svc = next(s for s in self._p.services()
                       if s.UUID().UUIDString() == NEEWER_SVC)
            self._p.discoverCharacteristics_forService_(None, svc)
            self._d.chr_done.wait(timeout)
            self._write_ch = next(c for c in svc.characteristics()
                                  if c.properties() & 0x08)

        @property
        def name(self) -> str:
            return str(self._p.name())

        def send(self, data: bytes) -> None:
            self._d.wrote.clear()
            self._p.writeValue_forCharacteristic_type_(
                Foundation.NSData.dataWithBytes_length_(data, len(data)),
                self._write_ch, 0)
            self._d.wrote.wait(5)

        def close(self) -> None:
            self._mgr.cancelPeripheralConnection_(self._p)


# ========================================================== bleak backend

else:
    import asyncio
    import threading

    class _AsyncLoopMixin:
        """Runs an event loop on a dedicated thread so sync methods can wait on it."""

        def _start_loop(self, timeout: float):
            self._timeout = timeout
            self._loop = asyncio.new_event_loop()
            threading.Thread(target=self._loop.run_forever, daemon=True).start()

        def _run(self, coro):
            return asyncio.run_coroutine_threadsafe(
                coro, self._loop).result(self._timeout + 5)

        def _stop_loop(self):
            self._loop.call_soon_threadsafe(self._loop.stop)

    class _WinConnectedNeewer(_LightMixin, _AsyncLoopMixin):
        """A handle that piggybacks (via WinRT) onto a NEEWER already
        connected to this PC (Windows).

        A unit held by the control app stops BLE advertising and therefore
        cannot be found by scanning, but the Windows BLE stack shares GATT
        connections across apps on the same PC, so it can be enumerated as
        an already-connected device and written to directly (the same idea
        as the CoreBluetooth piggyback on macOS). Raises RuntimeError if no
        connected NEEWER is found (the caller falls back to scanning).
        """

        def __init__(self, timeout: float = 15.0):
            self._start_loop(timeout)
            try:
                self._run(self._connect())
            except Exception:
                self._stop_loop()
                raise

        async def _connect(self):
            import uuid as _uuid

            from winrt.windows.devices.bluetooth import (
                BluetoothConnectionStatus, BluetoothLEDevice)
            from winrt.windows.devices.bluetooth.genericattributeprofile import (
                GattCharacteristicProperties, GattCommunicationStatus,
                GattOpenStatus, GattSharingMode, GattWriteOption)
            from winrt.windows.devices.enumeration import DeviceInformation

            self._GattWriteOption = GattWriteOption
            self._GattCommunicationStatus = GattCommunicationStatus

            sel = BluetoothLEDevice.get_device_selector_from_connection_status(
                BluetoothConnectionStatus.CONNECTED)
            infos = await DeviceInformation.find_all_async_aqs_filter(sel)
            info = next((infos.get_at(i) for i in range(infos.size)
                         if "NEEWER" in (infos.get_at(i).name or "").upper()),
                        None)
            if info is None:
                raise RuntimeError("No connected NEEWER light found")
            self._name = info.name
            self._dev = await BluetoothLEDevice.from_id_async(info.id)
            svcs = await self._dev.get_gatt_services_for_uuid_async(
                _uuid.UUID(NEEWER_SVC))
            if svcs.status != GattCommunicationStatus.SUCCESS or svcs.services.size == 0:
                raise RuntimeError("Cannot access the NEEWER service")
            svc = svcs.services.get_at(0)
            # If the control app has opened the service exclusively, the
            # shared open fails with SHARING_VIOLATION and characteristics
            # cannot be enumerated either (observed in practice).
            open_st = await svc.open_async(GattSharingMode.SHARED_READ_AND_WRITE)
            if open_st == GattOpenStatus.SHARING_VIOLATION:
                raise RuntimeError(
                    "The control app is holding the light exclusively. "
                    "Quit the NEEWER control app on the PC and try again")
            chs = await svc.get_characteristics_async()
            self._write_ch = None
            self._write_opt = GattWriteOption.WRITE_WITH_RESPONSE
            for i in range(chs.characteristics.size):
                ch = chs.characteristics.get_at(i)
                p = ch.characteristic_properties
                if p & GattCharacteristicProperties.WRITE:
                    self._write_ch = ch
                    break
                if (p & GattCharacteristicProperties.WRITE_WITHOUT_RESPONSE
                        and self._write_ch is None):
                    self._write_ch = ch
                    self._write_opt = GattWriteOption.WRITE_WITHOUT_RESPONSE
            if self._write_ch is None:
                raise RuntimeError("No writable characteristic found")

        async def _write(self, data: bytes):
            from winrt.windows.storage.streams import DataWriter
            w = DataWriter()
            # winrt 3.x's write_bytes requires a bytes-like object
            # (passing a list raises TypeError: a bytes-like object is required)
            w.write_bytes(bytes(data))
            status = await self._write_ch.write_value_with_option_async(
                w.detach_buffer(), self._write_opt)
            if status != self._GattCommunicationStatus.SUCCESS:
                raise RuntimeError(f"BLE write failed (status={status})")

        @property
        def name(self) -> str:
            return self._name

        def send(self, data: bytes) -> None:
            self._run(self._write(bytes(data)))

        def close(self) -> None:
            try:
                self._dev.close()
            finally:
                self._stop_loop()

    class _BleakNeewer(_LightMixin, _AsyncLoopMixin):
        """A handle that finds and connects to a NEEWER directly via bleak's
        advertisement scan.

        For a unit not held by any app (i.e. advertising).
        """

        def __init__(self, timeout: float = 15.0):
            from bleak import BleakClient, BleakScanner
            self._start_loop(timeout)

            def _match(dev, adv):
                nm = (dev.name or adv.local_name or "").upper()
                uuids = [str(u).lower() for u in (adv.service_uuids or [])]
                return "NEEWER" in nm or NEEWER_SVC.lower() in uuids

            try:
                dev = self._run(
                    BleakScanner.find_device_by_filter(_match, timeout=timeout))
                if dev is None:
                    raise RuntimeError(
                        "No NEEWER light found (check that it is powered on; "
                        "it will not be found if another device such as a "
                        "phone is connected to it)")
                self._name = dev.name or "NEEWER"
                self._client = BleakClient(dev)
                self._run(self._client.connect())
                self._write_ch = self._find_write_char()
            except Exception:
                self._stop_loop()
                raise

        def _find_write_char(self):
            svc = self._client.services.get_service(NEEWER_SVC)
            if svc is None:  # some units use a different service UUID; fall back to a full scan
                for s in self._client.services:
                    for ch in s.characteristics:
                        if {"write", "write-without-response"} & set(ch.properties):
                            return ch
                raise RuntimeError("No writable characteristic found")
            for ch in svc.characteristics:
                if "write" in ch.properties:
                    return ch
            for ch in svc.characteristics:
                if "write-without-response" in ch.properties:
                    return ch
            raise RuntimeError("No writable characteristic found")

        @property
        def name(self) -> str:
            return self._name

        def send(self, data: bytes) -> None:
            response = "write" in self._write_ch.properties
            self._run(self._client.write_gatt_char(
                self._write_ch, bytes(data), response=response))

        def close(self) -> None:
            try:
                self._run(self._client.disconnect())
            finally:
                self._stop_loop()

    def _win_neewer(timeout: float = 15.0):
        """Windows: try piggybacking on an already-connected device, then
        fall back to an advertisement scan."""
        try:
            return _WinConnectedNeewer(timeout)
        except Exception as e:
            print(f"Cannot piggyback on a connected device ({e}) -> falling "
                  f"back to scanning",
                  file=sys.stderr)
            return _BleakNeewer(timeout)


# Public name: pick the backend for the current platform
NeewerLight = _MacNeewer if IS_MAC else _win_neewer


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] not in ("on", "off", "cct", "hsi"):
        print(__doc__)
        return 1
    light = NeewerLight()
    try:
        if args[0] == "on":
            light.power(True)
            print(f"{light.name}: on")
        elif args[0] == "off":
            light.power(False)
            print(f"{light.name}: off")
        elif args[0] == "cct":
            brt, kelvin = int(args[1]), int(args[2])
            gm = int(args[3]) if len(args) > 3 else 50
            light.set_cct(brt, kelvin, gm)
            print(f"{light.name}: brightness {brt}% / {kelvin}K / GM{gm}")
        else:
            hue, sat, inten = int(args[1]), int(args[2]), int(args[3])
            light.set_hsi(hue, sat, inten)
            print(f"{light.name}: HSI {hue} deg / saturation {sat}% / brightness {inten}%")
    finally:
        light.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
