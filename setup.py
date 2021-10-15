import sys
from setuptools import setup

if sys.version_info.major < 3:
    sys.exit('Sorry, this library only supports Python 3')

setup(
    name='littlefish',
    packages=['littlefish', 'littlefish.background', 'littlefish.sessiondata'],
    include_package_data=True,
    version='0.0.63',
    description='Flask webapp utility functions by Little Fish Solutions LTD',
    author='Stephen Brown (Little Fish Solutions LTD)',
    author_email='opensource@littlefish.solutions',
    url='https://github.com/stevelittlefish/littlefish',
    download_url='https://github.com/stevelittlefish/littlefish/archive/v0.0.63.tar.gz',
    keywords=['flask', 'utility', 'time', 'pager'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Framework :: Flask',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries'
    ],
    install_requires=[
        'geoip2>=2.4.2',
        'beautifulsoup4>=3.5.0.0',
        'Pillow>=4.0.0',
        'SQLAlchemy>=1.1.0',
        'PyMarkovChain>=1.8',
        'pytz>=2019.1',
        'python-dateutil>=2.6.0',
        'Flask>=0.12.0',
        'Flask-SQLAlchemy>=2.0',
        'Jinja2>=2.9.0',
        'IPy>=0.83',
        'lxml>=3.7.0',
        'PyYAML>=5.3.1'
    ],
    extras_require={
        'pdfsigner': [
            'endesive>=1.2.3',
            'pyOpenSSL>=19.0.0'
        ],
        'celery': [
            'celery>=4.3.0'
        ],
        'redis': [
            'redis>=3.2.1'
        ],
    }
)

