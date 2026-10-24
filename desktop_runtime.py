"""Windows background execution and a private WebView2 window without an app bridge."""
import ipaddress
import threading
from urllib.parse import urlparse

AD_HOSTS = {'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
            'adservice.google.com', 'ads.youtube.com', 'ads.facebook.com',
            'adnxs.com', 'taboola.com', 'outbrain.com', 'criteo.com', 'scorecardresearch.com'}


def public_url(value):
    parsed = urlparse(str(value))
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in {'http', 'https'} or not host or parsed.username or parsed.password:
        raise ValueError('Usa una dirección pública http o https.')
    if host == 'localhost' or host.endswith(('.localhost', '.local')) or '.' not in host:
        raise ValueError('El navegador privado no permite direcciones locales.')
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError('El navegador privado no permite direcciones locales.')
    except ValueError as exc:
        if str(exc).startswith('El navegador'):
            raise
    return str(value)


def blocked_url(url):
    try:
        public_url(url)
    except ValueError:
        return True
    host = (urlparse(url).hostname or '').lower()
    return any(host == domain or host.endswith('.' + domain) for domain in AD_HOSTS)


class DesktopRuntime:
    def __init__(self):
        self.window = None
        self.browser = None
        self.detected = []
        self.blocked = 0
        self.exiting = False
        self.stop = threading.Event()
        self.tray = None
        self.lock = threading.RLock()

    def bind(self, window, settings, manager, collections):
        self.window, self.settings, self.manager, self.collections = window, settings, manager, collections

        def ready():
            if self.tray:
                return
            from System import Action
            def setup():
                from System.Drawing import Icon
                from System.Windows.Forms import NotifyIcon, ContextMenuStrip
                from app_paths import APP_DIR
                tray = NotifyIcon()
                tray.Icon = Icon(str(APP_DIR / 'static' / 'app.ico'))
                tray.Text = 'VideoFlow Local'
                menu = ContextMenuStrip()
                show = menu.Items.Add('Abrir VideoFlow')
                show.Click += lambda *_: window.show()
                exit_item = menu.Items.Add('Salir y detener los trabajos')
                def leave(*_):
                    self.exiting = True
                    window.destroy()
                exit_item.Click += leave
                tray.DoubleClick += lambda *_: window.show()
                tray.ContextMenuStrip = menu
                tray.Visible = True
                self.tray = tray
            window.native.Invoke(Action(setup))
        window.events.loaded += ready

        def power():
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.SetThreadExecutionState.argtypes = [ctypes.c_uint]
            kernel.SetThreadExecutionState.restype = ctypes.c_uint
            try:
                while not self.stop.is_set():
                    active = manager.count_unfinished() or any(j['status'] == 'Leyendo' for j in collections.list())
                    keep = settings.load().get('keep_awake', True) and active
                    kernel.SetThreadExecutionState(0x80000001 if keep else 0x80000000)
                    self.stop.wait(3)
            finally:
                kernel.SetThreadExecutionState(0x80000000)
        threading.Thread(target=power, daemon=True).start()

    def closing(self):
        if not self.exiting and self.settings.load().get('background_mode', True):
            if self.tray:
                self.window.hide()
            else:
                self.window.minimize()
            from app import private_vault
            private_vault.close()
            return False
        return True

    def shutdown(self):
        self.stop.set()
        if self.tray:
            self.tray.Visible = False
            self.tray.Dispose()

    def open_browser(self, url):
        public_url(url)
        if not self.window:
            raise ValueError('Abre la aplicación de escritorio para usar el navegador privado.')
        from System import Action, Uri
        from System.Drawing import Color, Font, Size, Icon, ContentAlignment
        from System.IO import MemoryStream
        from System.Windows.Forms import Form, DockStyle, TableLayoutPanel, ColumnStyle, SizeType, Button, TextBox, Label, Keys, Padding, FlatStyle, FormStartPosition
        from Microsoft.Web.WebView2.WinForms import WebView2, CoreWebView2CreationProperties
        from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext, CoreWebView2PermissionState
        from app_paths import DATA_DIR, APP_DIR
        palette = self.window.evaluate_js("({background:getComputedStyle(document.documentElement).getPropertyValue('--surface-solid').trim(),foreground:getComputedStyle(document.documentElement).getPropertyValue('--text').trim()})") or {}
        from System.Drawing import ColorTranslator

        def show():
            if self.browser and not self.browser.IsDisposed:
                self.browser.Activate()
                self.browser_view.CoreWebView2.Navigate(url)
                return
            form, view = Form(), WebView2()
            form.Text, form.Width, form.Height = 'VideoFlow · Navegador privado', 1150, 780
            form.MinimumSize = Size(800, 500)
            form.StartPosition = FormStartPosition.CenterParent
            form.Font = Font('Segoe UI', 10)
            form.Icon = Icon(str(APP_DIR / 'static' / 'app.ico'))
            form.BackColor = ColorTranslator.FromHtml(palette.get('background', '#141b29'))
            form.ForeColor = ColorTranslator.FromHtml(palette.get('foreground', '#eef3ff'))
            bar = TableLayoutPanel()
            bar.ColumnCount, bar.RowCount = 4, 1
            bar.Dock, bar.Height = DockStyle.Top, 64
            bar.Padding = Padding(10)
            for style in (ColumnStyle(SizeType.Absolute, 48), ColumnStyle(SizeType.Percent, 100), ColumnStyle(SizeType.Absolute, 56), ColumnStyle(SizeType.Absolute, 165)):
                bar.ColumnStyles.Add(style)
            address = TextBox()
            address.Width, address.Text = 730, url
            address.BackColor, address.ForeColor = form.BackColor, form.ForeColor
            back, go, label = Button(), Button(), Label()
            back.Text, go.Text = '←', 'Ir'
            back.Width, go.Width = 42, 45
            label.Text, label.Width = 'Privado · AdBlock', 150
            label.TextAlign = ContentAlignment.MiddleCenter
            for control in (back, address, go, label):
                control.Dock = DockStyle.Fill
                control.Margin = Padding(5)
            for button in (back, go):
                button.FlatStyle = FlatStyle.Flat
                button.FlatAppearance.BorderSize = 1
                button.BackColor, button.ForeColor = form.BackColor, form.ForeColor
            bar.Controls.Add(back)
            bar.Controls.Add(address)
            bar.Controls.Add(go)
            bar.Controls.Add(label)
            props = CoreWebView2CreationProperties()
            props.UserDataFolder = str(DATA_DIR / 'private-browser')
            props.set_IsInPrivateModeEnabled(True)
            view.CreationProperties, view.Dock = props, DockStyle.Fill
            form.Controls.Add(view)
            form.Controls.Add(bar)
            with self.lock:
                self.detected, self.blocked = [], 0

            def remember(value, kind):
                try:
                    public_url(value)
                except ValueError:
                    return
                with self.lock:
                    if not any(item['url'] == value for item in self.detected):
                        self.detected.append(dict(url=value, kind=kind))
                        self.detected = self.detected[-200:]

            def request_resource(sender, args):
                value = str(args.Request.Uri)
                if blocked_url(value):
                    args.Response = view.CoreWebView2.Environment.CreateWebResourceResponse(MemoryStream(), 403, 'Blocked', 'Content-Type: text/plain')
                    with self.lock:
                        self.blocked += 1
                    label.Text = f'Bloqueados: {self.blocked}'

            def response_resource(sender, args):
                headers = args.Response.Headers
                content_type = str(headers.GetHeader('Content-Type')) if headers.Contains('Content-Type') else ''
                if content_type.startswith(('video/', 'audio/')) or any(t in content_type.lower() for t in ('mpegurl', 'dash+xml')):
                    remember(str(args.Request.Uri), 'Recurso multimedia')

            def navigating(sender, args):
                try:
                    public_url(str(args.Uri))
                except ValueError:
                    args.Cancel = True

            def popup(sender, args):
                args.Handled = True
                try:
                    public_url(str(args.Uri))
                    if not blocked_url(str(args.Uri)):
                        view.CoreWebView2.Navigate(str(args.Uri))
                except ValueError:
                    pass

            def ready(sender, args):
                if not args.IsSuccess:
                    label.Text = 'WebView2 no disponible'
                    return
                core = view.CoreWebView2
                core.Settings.AreDevToolsEnabled = False
                core.Settings.IsPasswordAutosaveEnabled = False
                core.Settings.IsGeneralAutofillEnabled = False
                core.AddWebResourceRequestedFilter('*', CoreWebView2WebResourceContext.All)
                core.WebResourceRequested += request_resource
                core.WebResourceResponseReceived += response_resource
                core.NavigationStarting += navigating
                core.NewWindowRequested += popup
                def deny_download(sender, args):
                    remember(str(args.DownloadOperation.Uri), 'Descarga detectada')
                    args.Cancel = True
                def deny_permission(sender, args):
                    args.State = CoreWebView2PermissionState.Deny
                core.DownloadStarting += deny_download
                core.PermissionRequested += deny_permission
                def completed(*_):
                    address.Text = str(core.Source)
                    remember(address.Text, 'Página visitada')
                core.NavigationCompleted += completed
                core.Navigate(url)

            def navigate(*_):
                try:
                    destination = public_url(address.Text)
                    if view.CoreWebView2:
                        view.CoreWebView2.Navigate(destination)
                except ValueError:
                    label.Text = 'URL no válida'
            go.Click += navigate
            def key(sender, args):
                if args.KeyCode == Keys.Enter:
                    args.SuppressKeyPress = True
                    navigate()
            address.KeyDown += key
            def previous(*_):
                if view.CoreWebView2 and view.CoreWebView2.CanGoBack:
                    view.CoreWebView2.GoBack()
            back.Click += previous
            view.CoreWebView2InitializationCompleted += ready
            form.FormClosed += lambda *_: view.Dispose()
            self.browser, self.browser_view = form, view
            form.Show(self.window.native)
            view.EnsureCoreWebView2Async(None)
        self.window.native.Invoke(Action(show))


runtime = DesktopRuntime()
