"""Shared playback clock and window handoff for local desktop players."""
import math
import threading
import time


def normalize_state(data):
    result = {}
    for key, minimum, maximum in [('position', 0, 8640000), ('duration', 0, 8640000),
                                   ('volume', 0, 1), ('rate', .25, 4), ('brightness', 50, 150)]:
        if key in data:
            value = float(data[key])
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError('Estado del reproductor no válido.')
            result[key] = value
    for key in ('playing', 'muted'):
        if key in data:
            if not isinstance(data[key], bool):
                raise ValueError('Estado del reproductor no válido.')
            result[key] = data[key]
    return result


class PlayerSessions:
    def __init__(self, clock=time.monotonic):
        self.lock = threading.RLock()
        self.clock = clock
        self.items = {}
        self.windows = {}

    def open(self, token):
        with self.lock:
            self.items[token] = dict(position=0., duration=0., volume=1., rate=1., brightness=100.,
                                     playing=False, muted=False, owner='main', revision=0, stamp=self.clock())

    def snapshot(self, token):
        with self.lock:
            state = self.items[token].copy()
            if state['playing']:
                state['position'] += max(0, self.clock() - state['stamp']) * state['rate']
            if state['duration'] > 0 and state['position'] >= state['duration']:
                state['position'] = state['duration']; state['playing'] = False
            state.pop('stamp')
            return state

    def update(self, token, changes, *, owner=None, report_role=None, revision=None):
        changes = normalize_state(changes)
        with self.lock:
            state = self.snapshot(token)
            if report_role is not None and (state['owner'] != report_role or state['revision'] != revision):
                return state
            state.update(changes)
            if state['duration'] > 0:
                state['position'] = min(state['position'], state['duration'])
            if owner:
                state['owner'] = owner
            if report_role is None:
                state['revision'] += 1
            state['stamp'] = self.clock()
            self.items[token] = state
            return self.snapshot(token)

    def release(self, token, window):
        with self.lock:
            if self.windows.get(token) is not window:
                return
            self.windows.pop(token, None)
            self.update(token, {}, owner='main')


sessions = PlayerSessions()
