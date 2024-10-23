#! /usr/bin/env python3
''' URL Specific Browser Launcher '''

from urllib.parse import urlparse
import subprocess
import argparse
import logging
import syslog
import pathlib
import shutil
import yaml
import dbus

def http_url(url):
    ''' URL checker '''

    if (url.startswith('http://') or
        url.startswith('https://') or
        url.startswith('ext+container:') or
        '://' not in url):
        return url

    syslog.syslog(syslog.LOG_ERR, f'{__file__}: not an HTTP/HTTPS URL: {url}')
    raise argparse.ArgumentTypeError(f'Not an HTTP/HTTPS URL: {url}')

def dbus_notification(**kwargs: str) -> None:
    ''' Send Notification over DBUS '''

    item = 'org.freedesktop.Notifications'
    notify_interface = dbus.Interface(
        dbus.SessionBus().get_object(item, f'/{item.replace(".", "/")}'), item)

    # https://specifications.freedesktop.org/notification-spec/latest/ar01s09.html#command-notify
    notify_interface.Notify(
        '', # app_name
        0, # replaces_id
        '', # app_icon
        kwargs['summary'], # summary
        kwargs['body'], # body
        [], # actions
        {"urgency": kwargs['urgency']}, # hints
        3000
    )

    logging.info('[USBROWSER] Notification urgency: [%s], summary: [%s], message: [%s]',
                    kwargs['urgency'], kwargs['summary'], repr(kwargs['body']))


def launch(bw_name, bw_data, url):
    ''' Browser Launcher '''

    if shutil.which(bw_data['executable']):
        cmd = [bw_data['executable']]
        logging.info('[USBROWSER] Browser `%s` with executable `%s`',
                        bw_name, bw_data['executable'])

        change_url = bw_data.get('change_url', {})
        url_prefix = change_url.get('prefix', '')
        transform_url = change_url.get('transform_original_url', [])

        for transform in transform_url:
            if (transform.get('from', '') != ''
                and transform.get('to', '') != ''):
                url = url.replace(
                    transform.get('from', ''),
                    transform.get('to', ''))

        if url_prefix != '':
            url = url_prefix + url

        logging.info('[USBROWSER] URL is `%s`', url)

        if 'arguments_list' in bw_data and len(bw_data['arguments_list']) > 0:
            for arg_key, arg_value in bw_data['arguments_list'].items():
                if bw_data['arguments_delimiter']:
                    argument_delimiter = bw_data['arguments_delimiter']
                else:
                    argument_delimiter = ''

                logging.info(
                    '[USBROWSER] Arguments list element is `%s%s%s`',
                    arg_key, argument_delimiter, arg_value)

                cmd.append(
                    f'{arg_key}{argument_delimiter}{arg_value}')

        cmd.append(url)

        logging.info('[USBROWSER] Command is `%s`', ' '.join(cmd))

        try:
            subprocess.Popen(cmd, start_new_session=True)
        except subprocess.CalledProcessError:
            syslog.syslog(
                syslog.LOG_ERR,
                f'{__file__}: could not open URL with browser '
                f'{bw_name}: {url}'
            )
            raise
    else:
        dbus_notification(
            urgency = 2,
            summary = 'URL Specific Browser-launcher',
            body = f'Cannot find executable `{bw_data["executable"]}` '
                   f'to launch {url}'
        )
        logging.critical('[USBROWSER] Cannot find executable `%s`',
                bw_data['executable'])
        syslog.syslog(syslog.LOG_ERR,
                f'{__file__}: Cannot find executable `{bw_data["executable"]}`'
            )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='URL Specific Browser Launcher',
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

    config = {"default":{"executable": "chromium"}}

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel)

    parsed = urlparse(args.url)
    PARSED_PATH = '/' if parsed.path == '' else parsed.path

    logging.debug('[USBROWSER] Setting default config:\n%s', yaml.dump(config, indent=2))
    logging.debug('[USBROWSER] Reading system and user config files')

    paths = [
        '/etc/usbrowser.yaml',
        f'{pathlib.Path.home()}/.config/usbrowser.yaml'
    ]
    for path in paths:
        try:
            with open(path, 'r', encoding="utf-8") as file:
                logging.debug('[USBROWSER] Found config file: %s', path)

                data = yaml.safe_load(file)
                logging.debug('[USBROWSER] Data:\n%s', yaml.dump(data, indent=2))

                for browser_name, browser_data in data.items():
                    logging.debug(
                        '[USBROWSER] Adding `%s` config from `%s` config file',
                        browser_name, path)

                    if browser_name not in config:
                        logging.debug('[USBROWSER] New browser - all items added')
                        config[browser_name] = browser_data
                    else:
                        for match_url_name, match_url_list in browser_data.items():
                            logging.debug(
                                '[USBROWSER] Add match_url details '
                                '`%s` to `%s` browser',
                                match_url_name, browser_name)
                            config[browser_name][
                                match_url_name] = match_url_list

        except FileNotFoundError:
            logging.debug('[USBROWSER] Unable to find config file: %s', path)

    logging.debug('[USBROWSER] Config files read - Final result:\n%s', yaml.dump(config, indent=2))

    FOUND_BROWSER = False
    for browser_name, browser_data in config.items():
        if FOUND_BROWSER:
            break

        logging.debug(
            '[USBROWSER] Checking to see if `%s` matches the supplied path',
            browser_name)
        match_urls = browser_data.get('urls', {})
        for match_url_name, match_url_list in match_urls.items():
            if FOUND_BROWSER:
                break

            logging.debug('[USBROWSER] Parsing the list of `%s` urls',
                            match_url_name)

            for match_url in match_url_list:
                if FOUND_BROWSER:
                    break

                match_url_scheme = match_url.get('scheme', '..EMPTY..')
                match_url_domain = match_url.get('domain', '..EMPTY..')
                match_url_domain_end = match_url.get(
                                        'domain_suffix', '..EMPTY..')
                match_url_path_start = '/' + match_url.get('path_start', '')

                logging.debug(
                    '[USBROWSER] Checking to see whether the '
                    'scheme of `%s` matches `%s`',
                    match_url_scheme, parsed.scheme
                )

                if match_url_scheme in ('..EMPTY..', parsed.scheme):
                    logging.debug(
                        '[USBROWSER] Matching domain `%s` with '
                        'match_url_domain `%s` or match_url_domain_end `%s`',
                        parsed.hostname, match_url_domain, match_url_domain_end
                    )

                    if (parsed.hostname == match_url_domain or
                        parsed.hostname.endswith(match_url_domain_end) or
                        (match_url_domain == '..EMPTY..'
                            and match_url_domain_end == '..EMPTY..')):
                        logging.debug(
                            '[USBROWSER] Matching path `%s` with '
                            'match_url_path_start `%s`',
                            PARSED_PATH, match_url_path_start
                        )

                        if PARSED_PATH.startswith(match_url_path_start):
                            logging.debug(
                                '[USBROWSER] Found a match. Ceasing '
                                'any further checks.')
                            FOUND_BROWSER = True
                            launch(browser_name, browser_data, args.url)

    if not FOUND_BROWSER:
        logging.debug('[USBROWSER] Using default browser')
        launch("default", config["default"], args.url)
