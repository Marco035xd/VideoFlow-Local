"""Native window controls and a local copy of the selected player background."""
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def run_on_form(window, operation):
    form = window.native
    if form.InvokeRequired:
        from System import Action
        form.Invoke(Action(lambda: operation(form)))
    else:
        operation(form)


def set_opacity(window, percent):
    run_on_form(window, lambda form: setattr(form, 'Opacity', percent / 100))


def resize_window(window, direction):
    from System.Windows.Forms import Screen

    def resize(form):
        area = Screen.FromControl(form).WorkingArea
        minimum = form.MinimumSize
        scale = 1.2 if direction == 1 else 1 / 1.2
        width = min(area.Width, max(minimum.Width, round(form.Width * scale)))
        height = min(area.Height, max(minimum.Height, round(form.Height * scale)))
        left = min(area.Right - width, max(area.Left, form.Left))
        top = min(area.Bottom - height, max(area.Top, form.Top))
        form.SetBounds(left, top, width, height)

    run_on_form(window, resize)


def save_background(path, data):
    # Publish only a complete image so that other open players can reload it safely.
    with NamedTemporaryFile(dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
