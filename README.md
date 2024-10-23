# URL Specific Browser Launcher

This code is highly inspired by [a stack overflow answer](https://askubuntu.com/a/1164362/212).

The default internal configuration declares `chromium` as the default browser to launch.
Places where the script will look for its configurations:
 - `/etc/usbrowser.yaml`
 - `~/.config/usbrowser.yaml`.

Configuration sample: [usbrowser.yaml](usbrowser.yaml)

## Installation

Copy the `usbrowser.py` file to `~/.local/bin` and make it executable:
```bash
$ mkdir -p ~/.local/bin
$ cp usbrowser.py ~/.local/bin/
$ chmod +x ~/.local/bin/usbrowser.py
```

Create desktop file `~/.local/share/applications/usbrowser.desktop`:
```ini
[Desktop Entry]
Name=HTTP URL handler
Comment=Open an HTTP/HTTPS URL with a particular browser
TryExec=usbrowser.py
Exec=usbrowser.py %u
X-MultipleArgs=false
Type=Application
Terminal=false
NoDisplay=true
MimeType=x-scheme-handler/http;x-scheme-handler/https
```

Register the created desktop file with the `x-scheme-handler/http` and `x-scheme-handler/https` mimetypes:

```bash
$ gio mime x-scheme-handler/http usbrowser.desktop
Set usbrowser.desktop as the default for x-scheme-handler/http

$ gio mime x-scheme-handler/https usbrowser.desktop
Set usbrowser.desktop as the default for x-scheme-handler/https
```

Check using `gio` that settings have been applied:
```bash
$ gio mime x-scheme-handler/http
Default application for “x-scheme-handler/http”: usbrowser.desktop
Registered applications:
    usbrowser.desktop
    librewolf.desktop
Recommended applications:
    usbrowser.desktop
    librewolf.desktop

$ gio mime x-scheme-handler/https
Default application for “x-scheme-handler/https”: usbrowser.desktop
Registered applications:
    usbrowser.desktop
    librewolf.desktop
Recommended applications:
    usbrowser.desktop
    librewolf.desktop
```

Check using `xdg-mime` that settings have been applied:
```bash
$ xdg-mime query default x-scheme-handler/http
usbrowser.desktop

$ xdg-mime query default x-scheme-handler/https
usbrowser.desktop
```

Test different URLs in accordance with the sample configuration:
```bash
# open default browser
$ gio open https://google.com

# open google chrome
$ gio open https://meet.google.com

# open librewolf
$ gio open https://example.com

# open torbrowser
$ gio open https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/
```

Update mimeinfo cache:
```bash
$ update-desktop-database ~/.local/share/applications
```

