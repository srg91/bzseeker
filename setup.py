from setuptools import setup, find_packages

from bzseeker import __version__ as bzseeker_version


setup(
    name='bzseeker',
    description='A small binary-search seeker'
                ' for search needed dates in log-files,'
                ' archived with bzip2.',
    version=bzseeker_version,
    author='Sergey Yurchik',
    author_email='srg91.snz@gmail.com',
    url='https://github.com/srg91/bzseeker',
    license='MIT',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'bzseeker = bzseeker.console:main'
        ]
    }
)

