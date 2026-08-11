from setuptools import setup, find_packages

setup(
    name="novavision-cap-ptz-tracking-onvif",
    version="0.0.1",
    author="DigiNova",
    author_email='info@diginova.com.tr',
    description="NOVAVISION PTZ Tracking (ONVIF)",
    url='https://github.com/novavision-ai/lib-onvif-ptz',
    license='MIT',
    install_requires=[
        'numpy>=1.21.0',           # Matris işlemleri için
        'opencv-python>=4.5.0',    # Görüntü işleme için
        'onvif-zeep-f>=1.0.0',     # ONVIF bağlantısı için (Kritik!)
        'simple-pid>=1.0.0',       # PID kontrolcüsü için
        'pydantic>=1.8.0',         # Model validasyonu için
        'requests>=2.25.0'         # API istekleri için
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(where="."),
    python_requires=">=3.6"
)