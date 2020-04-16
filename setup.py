import setuptools
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='reddit2epub',
    version='0.4.2',
    description='A CLI to convert reddit series into epub files',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/mircohaug/reddit2epub.git',
    author='Mirco Haug',
    author_email='python@mircohaug.de',
    packages=setuptools.find_packages(),
    install_requires=[
        'click==7.*',
        'praw==6.*',
        'EbookLib==0.17.*',
    ],
    entry_points={
        "console_scripts": ['reddit2epub = reddit2epub.reddit2epubCli:main_cli']
    },
    # from https://pypi.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Utilities"
    ],
)
