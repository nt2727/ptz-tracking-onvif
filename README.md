# PTZ Tracking (ONVIF) — NovaVision Capsule

ONVIF uyumlu PTZ (Pan-Tilt-Zoom) kameralar için PID tabanlı otomatik nesne takibi
capsule'ü. Üst akıştan (object detection / tracker) gelen `Detection` listesine
göre kamerayı hedefi kare merkezinde tutacak şekilde hareket ettirir.

## İki Executor

Bu capsule iki ayrı executor içerir; her ikisi de aynı `PackageModel` şemasını
ve aynı PID/ONVIF mantığını paylaşır, sadece kameraya **nasıl bağlanıldığı**
farklıdır:

- **`PTZTracking`** (manuel): `CameraIP`, `CameraPort`, `CameraUsername`,
  `CameraPassword` config'leri ile doğrudan belirtilen IP'ye bağlanır.
  Kameranın IP'sini biliyorsanız (çoğu durumda önerilen yöntem) bunu kullanın.
- **`PTZTrackingAuto`** (otomatik): Bağlanmadan önce ağda WS-Discovery ile
  ONVIF kamera arar, bulduğu ilk cihaza bağlanır. WS-Discovery'nin çalışması
  için `onvif` kütüphanesinin `onvif.util.discover` fonksiyonunu desteklemesi
  ve kameranın aynı subnet'te / multicast'e açık olması gerekir. Kamera NAT
  arkasındaysa veya üretici bulut eklentisi ONVIF'i gizliyorsa (bazı Tapo/TP-Link
  modellerinde olduğu gibi) otomatik keşif başarısız olabilir; bu durumda
  `PTZTracking` (manuel) executor'ü kullanın.

## Hareket Modları (`MovementType`)

- **`Follow`**: `inputDetections` içindeki hedefi (varsayılan: en yüksek
  confidence, `FollowTracker=true` ise sabit `trackerID`) PID kontrolcüsüyle
  sürekli takip eder.
- **`GoToPreset`**: Detection akışından bağımsız olarak kamerayı
  `DefaultPositionPreset` adlı önceden tanımlı preset pozisyonuna götürür.

`Follow` modunda, `MoveToPositionAfterIdleSeconds` saniye boyunca hiç detection
gelmezse kamera otomatik olarak `DefaultPositionPreset`'e döner (idle reset).

## Kurulum

```bash
# NovaVision SDK (ayrı repo, PyPI'de değil)
pip install git+https://github.com/novavision-ai/sdk.git
# veya lokal geliştirmede: pip install -e ../sdk

pip install -e .
```

`setup.py` içindeki bağımlılıklar: `numpy`, `opencv-python`, `onvif-zeep-async`
(kod async API kullanır), `simple-pid`, `pydantic<2`, `requests`.

## Konfigürasyon Notları

- **Varsayılan kimlik bilgileri**: `apps/` altındaki örnekler kolaylık için
  `admin/admin` kullanır. **Üretimde bu asla kullanılmamalı** — gerçek
  kamera kullanıcı adı/şifresini `ConfigCameraUsername` / `ConfigCameraPassword`
  ile mutlaka ayarlayın.
- ONVIF servisleri (`ContinuousMove`, `GotoPreset`) kameranın desteklemesini
  gerektirir; birçok tüketici kamerasında (ör. Tapo) ONVIF'in kamera
  uygulamasından/arayüzünden ayrıca etkinleştirilmesi gerekir ve port
  genelde `80` değil `2020`'dir — kameranızın kendi ONVIF portunu kontrol edin.

## Klasör Yapısı

```
capsules/PTZTracking/
├── apps/         # Örnek/manuel test scriptleri (inference, inference_auto, inference_sim, export)
├── src/
│   ├── classes/  # ONVIFWrapper, PIDController
│   ├── executors/# PTZTracking (manuel), PTZTrackingAuto (WS-Discovery)
│   ├── models/   # Pydantic PackageModel şeması
│   └── utils/    # yardımcı fonksiyonlar
├── resources/    # test görüntüsü/videosu (repo'ya dahil değildir, eklenmelidir)
├── notebooks/    # (opsiyonel) keşif/deney notebook'ları
└── tests/        # birim testleri
```

## Test

```bash
pytest capsules/PTZTracking/tests -v
```

Kamera olmadan çalışan birim testleri `PIDController` ve dead-zone/zoom
mantığını kapsar. Gerçek bir ONVIF kamerayla entegrasyon testi için
`capsules/PTZTracking/apps/inference.py` (manuel) veya `inference_auto.py`
(otomatik keşif) örnek scriptlerini kullanın.
