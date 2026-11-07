"""Effets sonores synthétisés procéduralement (aucun fichier audio requis).

Les sons sont générés en tâche de fond au lancement pour ne pas retarder
l'affichage du menu. Si le mixer n'est pas disponible, tout est silencieux.
"""
import math
import random
import threading
from array import array

import pygame

TAU = math.tau


def _env(i, n, attack=0.005, release=None, sr=44100):
    """Enveloppe attaque linéaire / décroissance exponentielle."""
    a = int(attack * sr)
    if i < a:
        return i / max(1, a)
    t = (i - a) / max(1, n - a)
    return (1 - t) ** (release if release else 2.0)


class _Synth:
    def __init__(self, sr):
        self.sr = sr

    def n(self, dur):
        return int(dur * self.sr)

    def tone(self, dur, f0, f1=None, wave='sine', vol=0.5, attack=0.004, curve=2.0, vibrato=0.0, vib_rate=6.0):
        n = self.n(dur)
        f1 = f0 if f1 is None else f1
        out = [0.0] * n
        phase = 0.0
        sr = self.sr
        for i in range(n):
            t = i / n
            f = f0 * (f1 / f0) ** t if f0 > 0 and f1 > 0 else f0 + (f1 - f0) * t
            if vibrato:
                f *= 1 + vibrato * math.sin(TAU * vib_rate * i / sr)
            phase += f / sr
            p = phase % 1.0
            if wave == 'sine':
                v = math.sin(TAU * p)
            elif wave == 'square':
                v = 1.0 if p < 0.5 else -1.0
            elif wave == 'saw':
                v = 2 * p - 1
            else:  # triangle
                v = 4 * abs(p - 0.5) - 1
            out[i] = v * vol * _env(i, n, attack, curve, sr)
        return out

    def noise(self, dur, vol=0.5, lp_start=0.9, lp_end=0.1, attack=0.002, curve=2.0):
        n = self.n(dur)
        out = [0.0] * n
        y = 0.0
        for i in range(n):
            t = i / n
            k = lp_start + (lp_end - lp_start) * t
            y += k * (random.uniform(-1, 1) - y)
            out[i] = y * vol * _env(i, n, attack, curve, self.sr)
        return out

    @staticmethod
    def mix(*tracks, offsets=None):
        offsets = offsets or [0] * len(tracks)
        length = max(len(t) + o for t, o in zip(tracks, offsets))
        out = [0.0] * length
        for t, o in zip(tracks, offsets):
            for i, v in enumerate(t):
                out[i + o] += v
        return out


class Audio:
    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.sfx_volume = 0.7
        self.ready = False
        self._loops = {}
        self._last_play = {}
        if self.enabled:
            freq, size, channels = pygame.mixer.get_init()
            if size != -16:
                self.enabled = False
                return
            self.sr = freq
            self.channels = channels
            try:
                pygame.mixer.set_num_channels(32)
            except Exception:
                pass
            threading.Thread(target=self._build_all, daemon=True).start()

    # ------------------------------------------------------------------
    def _to_sound(self, samples):
        clipped = array('h')
        ch = self.channels
        for v in samples:
            v = max(-1.0, min(1.0, v))
            s = int(v * 30000)
            for _ in range(ch):
                clipped.append(s)
        return pygame.mixer.Sound(buffer=clipped.tobytes())

    def _build_all(self):
        try:
            s = _Synth(self.sr)
            r = s.sr
            defs = {}
            defs['swing'] = lambda: s.noise(0.16, 0.35, 0.15, 0.6, attack=0.03, curve=1.5)
            defs['hit'] = lambda: s.mix(s.noise(0.09, 0.55, 0.8, 0.1), s.tone(0.12, 180, 60, 'sine', 0.6))
            defs['crit'] = lambda: s.mix(s.noise(0.1, 0.6, 0.9, 0.2), s.tone(0.14, 200, 50, 'sine', 0.6),
                                         s.tone(0.35, 1500, 1400, 'sine', 0.25, curve=3))
            defs['enemy_die'] = lambda: s.mix(s.tone(0.35, 300, 60, 'square', 0.18), s.noise(0.3, 0.35, 0.5, 0.05))
            defs['hurt'] = lambda: s.mix(s.tone(0.22, 220, 90, 'square', 0.22), s.noise(0.12, 0.3, 0.6, 0.1))
            defs['coin'] = lambda: s.mix(s.tone(0.08, 988, None, 'square', 0.12, curve=1.2),
                                         s.tone(0.22, 1319, None, 'square', 0.12, curve=2.5),
                                         offsets=[0, int(0.06 * r)])
            defs['iron'] = lambda: s.mix(s.tone(0.25, 1180, None, 'sine', 0.22, curve=4),
                                         s.tone(0.25, 1770, None, 'sine', 0.14, curve=5))
            defs['xp'] = lambda: s.tone(0.12, 600, 1200, 'triangle', 0.2)
            defs['levelup'] = lambda: s.mix(*[s.tone(0.35, f, None, 'square', 0.12, curve=2.5)
                                              for f in (523, 659, 784, 1047)],
                                            offsets=[0, int(0.09 * r), int(0.18 * r), int(0.27 * r)])
            defs['dash'] = lambda: s.noise(0.22, 0.32, 0.05, 0.5, attack=0.02, curve=1.3)
            defs['spin'] = lambda: s.mix(s.noise(0.38, 0.4, 0.1, 0.7, attack=0.05, curve=1.2),
                                         s.tone(0.38, 120, 300, 'saw', 0.08))
            defs['potion'] = lambda: s.mix(*[s.tone(0.07, f, f * 1.4, 'sine', 0.25) for f in (300, 380, 460)],
                                           s.tone(0.4, 520, 1040, 'triangle', 0.12),
                                           offsets=[0, int(0.08 * r), int(0.16 * r), int(0.2 * r)])
            defs['chest'] = lambda: s.mix(s.tone(0.25, 140, 90, 'saw', 0.12), s.noise(0.2, 0.2, 0.3, 0.1),
                                          *[s.tone(0.15, f, None, 'square', 0.08) for f in (1319, 1568, 1976)],
                                          offsets=[0, 0, int(0.2 * r), int(0.27 * r), int(0.34 * r)])
            defs['shoot'] = lambda: s.tone(0.18, 900, 200, 'square', 0.12)
            defs['slam'] = lambda: s.mix(s.tone(0.7, 90, 30, 'sine', 0.9, curve=1.6), s.noise(0.6, 0.6, 0.4, 0.02))
            defs['roar'] = lambda: s.mix(s.tone(1.2, 110, 70, 'saw', 0.25, attack=0.08, curve=1.4, vibrato=0.06, vib_rate=9),
                                         s.tone(1.2, 55, 40, 'square', 0.15, attack=0.1, curve=1.4),
                                         s.noise(1.0, 0.25, 0.2, 0.05, attack=0.1))
            defs['ui_hover'] = lambda: s.tone(0.03, 1400, None, 'sine', 0.08)
            defs['ui_click'] = lambda: s.mix(s.tone(0.06, 700, 500, 'square', 0.1), s.noise(0.03, 0.15, 0.9, 0.5))
            defs['portal'] = lambda: s.mix(*[s.tone(0.9, f, f * 1.01, 'sine', 0.12, attack=0.1, curve=1.5,
                                                    vibrato=0.01) for f in (220, 277, 330, 440)])
            defs['heartbeat'] = lambda: s.mix(s.tone(0.12, 60, 40, 'sine', 0.8), s.tone(0.12, 55, 38, 'sine', 0.6),
                                              offsets=[0, int(0.18 * r)])
            defs['victory'] = lambda: s.mix(*[s.tone(0.6, f, None, 'triangle', 0.15, curve=1.5)
                                              for f in (392, 523, 659, 784, 1047)],
                                            offsets=[int(i * 0.14 * r) for i in range(5)])
            defs['mimic'] = lambda: s.mix(s.tone(0.5, 160, 80, 'saw', 0.25, vibrato=0.1, vib_rate=14),
                                          s.noise(0.3, 0.3, 0.4, 0.1))
            for name, fn in defs.items():
                self.sounds[name] = self._to_sound(fn())
            self.ready = True
            # boucles d'ambiance (plus longues, générées en dernier)
            self.sounds['drone'] = self._to_sound(self._drone(s))
            self.sounds['boss_loop'] = self._to_sound(self._boss_loop(s))
        except Exception as e:  # le jeu doit rester jouable sans son
            print(f"[Audio] Synthèse impossible : {e}")

    def _drone(self, s):
        dur = 8.0
        n = s.n(dur)
        sr = s.sr
        out = [0.0] * n
        y = 0.0
        for i in range(n):
            t = i / sr
            lfo = 0.5 + 0.5 * math.sin(TAU * t / dur)  # boucle parfaite
            v = (math.sin(TAU * 55 * t) * 0.35 + math.sin(TAU * 55.5 * t) * 0.3 +
                 math.sin(TAU * 82.5 * t) * 0.12 * lfo + math.sin(TAU * 110 * t + math.sin(TAU * 0.25 * t)) * 0.06)
            y += 0.02 * (random.uniform(-1, 1) - y)
            out[i] = (v + y * 0.5) * 0.35
        return out

    def _boss_loop(self, s):
        bpm = 140
        beat = 60 / bpm
        dur = beat * 8
        n = s.n(dur)
        sr = s.sr
        out = [0.0] * n
        kick = s.tone(0.25, 120, 40, 'sine', 0.9, curve=2)
        snare = s.noise(0.15, 0.4, 0.9, 0.3)
        notes = [55, 55, 65.4, 55, 55, 73.4, 65.4, 49]
        for b in range(8):
            o = int(b * beat * sr)
            for i, v in enumerate(kick):
                if o + i < n:
                    out[o + i] += v
            if b % 2 == 1:
                for i, v in enumerate(snare):
                    if o + i < n:
                        out[o + i] += v
            bass = s.tone(beat * 0.9, notes[b], None, 'saw', 0.18, curve=1.2)
            for i, v in enumerate(bass):
                if o + i < n:
                    out[o + i] += v
        return [v * 0.6 for v in out]

    # ------------------------------------------------------------------
    def play(self, name, volume=1.0, cooldown=0.0):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        if cooldown:
            now = pygame.time.get_ticks()
            if now - self._last_play.get(name, -99999) < cooldown * 1000:
                return
            self._last_play[name] = now
        try:
            ch = snd.play()
            if ch:
                ch.set_volume(max(0.0, min(1.0, volume * self.sfx_volume)))
        except Exception:
            pass

    def loop(self, name, volume=0.5):
        """Démarre (une seule fois) une boucle d'ambiance."""
        if not self.enabled:
            return
        if name in self._loops:
            ch = self._loops[name]
            if ch.get_busy():
                ch.set_volume(volume * self.sfx_volume)
                return
        snd = self.sounds.get(name)
        if snd is None:
            return
        try:
            ch = snd.play(loops=-1, fade_ms=1500)
            if ch:
                ch.set_volume(volume * self.sfx_volume)
                self._loops[name] = ch
        except Exception:
            pass

    def stop_loop(self, name, fade=1000):
        ch = self._loops.pop(name, None)
        if ch:
            try:
                ch.fadeout(fade)
            except Exception:
                pass

    def stop_all_loops(self):
        for name in list(self._loops):
            self.stop_loop(name)


_audio = None


def get_audio():
    global _audio
    if _audio is None:
        _audio = Audio()
    return _audio


def sfx(name, volume=1.0, cooldown=0.0):
    get_audio().play(name, volume, cooldown)
