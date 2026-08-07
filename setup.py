import setuptools

setuptools.setup(
    name="novavision-cap-ptz-tracking-onvif",
    version="0.0.1",
    author="DigiNova",
    author_email='info@diginova.com.tr',
    description="NOVAVISION PTZ Tracking (ONVIF)",
    url='https://github.com/novavision-ai/lib-onvif-ptz',
    license='MIT',
    install_requires=[
        'numpy',
        'onvif-zeep-f',
        'simple-pid',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=[
        'novavision.cap.ptz-tracking-onvif',
        'novavision.cap.ptz-tracking-onvif.classes',
        'novavision.cap.ptz-tracking-onvif.executors',
        'novavision.cap.ptz-tracking-onvif.models',
        'novavision.cap.ptz-tracking-onvif.utils',
    ],
    package_dir={'novavision.cap.ptz-tracking-onvif': 'src'},
    python_requires=">=3.6"
)