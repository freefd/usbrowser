#! /usr/bin/env python3
''' URL Specific Browser-launcher '''

from urllib.parse import urlparse
import subprocess
import argparse
import logging
import syslog
import pathlib
import yaml

def http_url(url):
    ''' URL checker '''

    if (url.startswith('http://') or
        url.startswith('https://') or
        url.startswith('ext+container:') or
        '://' not in url):
        return url

    syslog.syslog(syslog.LOG_ERR, f'{__file__}: not an HTTP/HTTPS URL: {url}')
    raise argparse.ArgumentTypeError(f'Not an HTTP/HTTPS URL: {url}')

def launch(bw_name, bw_data, url):
    ''' Browser Launcher '''

    cmd = [bw_data['executable']]
    logging.info('browser = %s, %s', bw_name, bw_data['executable'])

    change_url = bw_data.get('change_url', {})
    url_prefix = change_url.get('prefix', '')
    transform_url = change_url.get('transform_original_url', [])

    for transform in transform_url:
        if transform.get('from', '') != '' and transform.get('to', '') != '':
            url = url.replace(transform.get('from', ''), transform.get('to', ''))

    if url_prefix != '':
        url = url_prefix + url

    logging.info('url = %s', url)

    if 'arguments_list' in bw_data and len(bw_data['arguments_list']) > 0:
        for argument_key, argument_value in bw_data['arguments_list'].items():
            if bw_data['arguments_delimiter']:
                argument_delimiter = bw_data['arguments_delimiter']
            else:
                argument_delimiter = ''

            logging.info( 'arguments_list element = %s%s%s',
                argument_key, argument_delimiter, argument_value)

            cmd.append(f'{argument_key}{argument_delimiter}{argument_value}')

    cmd.append(url)

    logging.info('command = %s', ' '.join(cmd))

    try :
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        syslog.syslog(
            syslog.LOG_ERR,
            f'{__file__}: could not open URL with browser '
            f'{bw_name}: {url}'
        )
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
    config = {"default":{"executable": "chromium"}}
    PARSED_PATH = '/' if parsed.path == '' else parsed.path
    logging.debug('Setting default config')
    logging.debug('Reading system and user config files')

    paths = [
        '/etc/usbrowser.yaml',
        f'{pathlib.Path.home()}/.config/usbrowser.yaml'
    ]
    for path in paths:
        try:
            with open(path, 'r', encoding="utf-8") as file:
                logging.debug('Found config file: %s', path)

                data = yaml.safe_load(file)
                logging.debug('Data: %s', data)

                for browser_name, browser_data in data.items():
                    logging.debug(
                        'Adding %s config from that config file', browser_name)

                    if browser_name not in config:
                        logging.debug('New browser - all items added')
                        config[browser_name] = browser_data
                    else:
                        for match_url_name, match_url_list in browser_data.items():
                            logging.debug(
                                'Add match_url details %s to that browser',
                                match_url_name
                            )
                            config[browser_name][
                                match_url_name] = match_url_list

        except FileNotFoundError:
            logging.debug('Unable to find config file: %s', path)

    logging.debug('Config files read - Final result: %s', config)

    FOUND_BROWSER = False
    for browser_name, browser_data in config.items():
        if FOUND_BROWSER:
            break

        logging.debug(
            'Checking to see if %s matches the supplied path', browser_name)
        match_urls = browser_data.get('urls', {})
        for match_url_name, match_url_list in match_urls.items():
            if FOUND_BROWSER:
                break

            logging.debug('Parsing the list of %s urls', match_url_name)

            for match_url in match_url_list:
                if FOUND_BROWSER:
                    break

                match_url_scheme = match_url.get('scheme', '..EMPTY..')
                match_url_domain = match_url.get('domain', '..EMPTY..')
                match_url_domain_end = match_url.get(
                                        'domain_suffix', '..EMPTY..')
                match_url_path_start = '/' + match_url.get('path_start', '')

                logging.debug(
                    'Checking to see whether the scheme of %s matches %s',
                    match_url_scheme, parsed.scheme
                )

                if match_url_scheme in ('..EMPTY..', parsed.scheme):
                    logging.debug(
                        'Matching domain %s with match_url_domain %s'
                        ' or match_url_domain_end %s',
                        parsed.netloc, match_url_domain, match_url_domain_end
                    )

                    if (parsed.netloc == match_url_domain or
                        parsed.netloc.endswith(match_url_domain_end) or
                        (match_url_domain == '..EMPTY..'
                            and match_url_domain_end == '..EMPTY..')):
                        logging.debug(
                            'Matching path %s with match_url_path_start %s',
                            PARSED_PATH, match_url_path_start
                        )

                        if PARSED_PATH.startswith(match_url_path_start):
                            logging.debug(
                                'Found a match. Ceasing any further checks.')
                            FOUND_BROWSER = True
                            launch(browser_name, browser_data, args.url)

    if not FOUND_BROWSER:
        logging.debug('Using default browser')
        launch("default", config["default"], args.url)
