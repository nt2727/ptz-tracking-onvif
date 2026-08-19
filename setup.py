import setuptools

setuptools.setup(
    name="ptz-tracking-onvif",
    version="0.0.1",
    author="DigiNova",
    author_email='info@diginova.com.tr',
    description="PTZ Tracking (ONVIF)",
    url='https://github.com/novavision-ai/ptz-tracking-onvif',
    license='MIT',
    install_requires=[
        'numpy>=1.21.0',
        'opencv-python>=4.5.0',
        'onvif-zeep-async==4.2.1',
        'simple-pid>=1.0.0',
        'pydantic>=2.0.0',
        'requests>=2.25.0',
    ],

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    packages=[
        'novavision.cap.ptz_tracking_onvif',
        'novavision.cap.ptz_tracking_onvif.classes',
        'novavision.cap.ptz_tracking_onvif.executors',
        'novavision.cap.ptz_tracking_onvif.models',
        'novavision.cap.ptz_tracking_onvif.utils'
    ],
    package_dir={'novavision.cap.ptz_tracking_onvif': 'src'},
    python_requires=">=3.8"
)
