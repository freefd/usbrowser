#! /usr/bin/env python3
# Inspired by https://askubuntu.com/a/1164362/212

from urllib.parse import urlparse
import subprocess
import argparse
import logging
import syslog
import yaml
import sys
import os


def http_url(url):
    if (
        url.startswith('http://') or 
        url.startswith('https://') or
        url.startswith('ext+container:') or
        '://' not in url
    ):
        return url
    else:
        syslog.syslog(syslog.LOG_ERR, sys.argv[0] + ": not an HTTP/HTTPS URL: '{}'".format(url))
        raise argparse.ArgumentTypeError(
            "Not an HTTP/HTTPS URL: '{}'".format(url))

def launch(browser_name, browser_data, url):
    logging.info("browser = '{}', '{}'".format(browser_name, browser_data['executable']))
    change_url = browser_data.get('change_url', {})
    url_prefix = change_url.get('prefix', '')
    transform_url = change_url.get('transform_original_url', [])
    for transform in transform_url:
        if transform.get('from', '') != '' and transform.get('to', '') != '':
            url = url.replace(transform.get('from', ''), transform.get('to', ''))
    if url_prefix != '':
        url = url_prefix + url
    logging.info("url = '{}'".format(url))
    cmd = [browser_data['executable'], url]
    try :
        status = subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        syslog.syslog(syslog.LOG_ERR, sys.argv[0] + "could not open URL with browser '{}': {}".format(browser_name, url))
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Handler for http/https URLs.',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='More verbose logging',
        dest="loglevel",
        default=logging.WARNING,
        action="store_const",
        const=logging.INFO,
    )
    parser.add_argument(
        '-d',
        '--debug',
        help='Enable debugging logs',
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
    )
    parser.add_argument(
        'url',
        type=http_url,
        help="URL starting with 'http://' or 'https://'",
    )
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)
    parsed = urlparse(args.url)
    logging.debug(parsed)
    if parsed.path == '':
        parsed_path = '/'
    else:
        parsed_path = parsed.path
    
    logging.debug("Setting default config")
    config = {"default":{"executable": "firefox"}}

    logging.debug("Reading system and user config files")
    paths = [
        '/etc/usbrowser_config.yml',
        os.path.expanduser('~/.usbrowser_config.yml')
    ]
    for path in paths:
        try:
            with open(path, 'r') as file:
                logging.debug("Found config file: {}".format(path))
                data = yaml.safe_load(file)
                logging.debug('Data: {}'.format(data))
                for browser_name, browser_data in data.items():
                    logging.debug("Adding {} config from that config file".format(browser_name))
                    if browser_name not in config:
                        logging.debug("New browser - all items added")
                        config[browser_name] = browser_data
                    else:
                        for match_url_name, match_url_list in browser_data.items():
                            logging.debug("Add match_url details {} to that browser".format(match_url_name))
                            config[browser_name][match_url_name] = match_url_list
        except FileNotFoundError:
            logging.debug("Unable to find config file: {}".format(path))
            pass  # Ignore missing files

    logging.debug("Config files read - Final result: {}".format(config))
    found_browser = False
    for browser_name, browser_data in config.items():
        if found_browser:
            break
        logging.debug("Checking to see if {} matches the supplied path".format(browser_name))
        match_urls = browser_data.get('urls', {})
        for match_url_name, match_url_list in match_urls.items():
            if found_browser:
                break
            logging.debug("Parsing the list of {} urls".format(match_url_name))
            for match_url in match_url_list:
                if found_browser:
                    break
                match=False
                match_url_scheme = match_url.get('scheme', '..EMPTY..')
                match_url_domain = match_url.get('domain', '..EMPTY..')
                match_url_domain_end = match_url.get('domain_suffix', '..EMPTY..')
                match_url_path_start = '/' + match_url.get('path_start', '')
                logging.debug("Checking to see whether the scheme of {} matches {}".format(match_url_scheme, parsed.scheme))
                if match_url_scheme == '..EMPTY..' or match_url_scheme == parsed.scheme:
                    logging.debug("Matching domain {} with match_url_domain {} or match_url_domain_end {}".format(parsed.netloc, match_url_domain, match_url_domain_end))
                    if parsed.netloc == match_url_domain or parsed.netloc.endswith(match_url_domain_end) or (match_url_domain == '..EMPTY..' and match_url_domain_end == '..EMPTY..'):
                        logging.debug("Matching path {} with match_url_path_start {}".format(parsed_path, match_url_path_start))
                        if parsed_path.startswith(match_url_path_start):
                            logging.debug("Found a match. Ceasing any further checks.")
                            found_browser = True
                            launch(browser_name, browser_data, args.url)

    if not found_browser:
        logging.debug("Using default browser.")
        launch("default", config["default"], args.url)
