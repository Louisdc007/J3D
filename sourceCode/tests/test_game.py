"""Tests automatiques (sans fenêtre) de Greed.

Lancement :  python sourceCode/tests/test_game.py
"""
import os
import random
import sys
import tempfile
import traceback

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ['HOME'] = tempfile.mkdtemp()          # sauvegardes isolées
os.environ['APPDATA'] = os.environ['HOME']
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, os.path.abspath(SRC))
os.chdir(os.path.abspath(SRC))

import builtins
_print = builtins.print
builtins.print = lambda *a, **k: None   # le jeu est bavard
import pygame  # noqa: E402
from game import Game  # noqa: E402
from entities.enemy import Enemy  # noqa: E402

RESULTS = []


def test(fn):
    RESULTS.append(fn)
    return fn


def frame(g, n=1, events=()):
    for _ in range(n):
        for e in events:
            pygame.event.post(e)
        events = ()
        g.events(); g.update(); g.draw(); g.clock.tick(0)


def walls_touching(g, rect):
    return [w for w in g.obstacle_sprites if w.rect.colliderect(rect)]


def enter_dungeon(g, kind='random'):
    g.current_dungeon_type = kind
    g.game_time = g.evening_duration
    g.game_state = 'loading'
    frame(g)
    assert g.game_state == 'dungeon'


@test
def player_cannot_cross_walls(g):
    random.seed(1)
    enter_dungeon(g)
    p = g.player
    p.max_health = p.health = 10 ** 6
    for direction in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7)):
        start = p.hitbox.copy()
        for k in range(240):
            p.direction = pygame.math.Vector2(direction)
            p.input = lambda: None                     # garde la direction forcée
            if k % 25 == 0:
                p.can_dash = True; p.start_dash()
            if k % 40 == 0:
                p.knockback = pygame.math.Vector2(direction) * 3000
            p.update(0.1 if k % 30 == 0 else 1 / 60)   # images lentes incluses
            assert not walls_touching(g, p.hitbox), f"joueur dans un mur (dir {direction}, frame {k})"
        p.hitbox.topleft = start.topleft; p.pos = pygame.math.Vector2(start.topleft)


@test
def enemies_cannot_cross_walls(g):
    random.seed(2)
    enter_dungeon(g)
    for e in list(g.attackable_sprites)[:12]:
        for k in range(150):
            e.direction = pygame.math.Vector2(random.choice((1, -1)), random.choice((1, -1)))
            e.knockback = e.direction * 2500 if k % 20 == 0 else e.knockback
            e.move(e.speed, 0.1 if k % 25 == 0 else 1 / 60)
            assert not walls_touching(g, e.hitbox), f"{e.tier} dans un mur"


@test
def hub_buildings_are_obstacles(g):
    g.return_to_menu()
    g.game_state = 'hub'
    g.player.inventory.update({'gold': 999, 'iron': 999})
    g.hub.build_mode_active = True
    g.hub.selected_blueprint = 'inn'
    g.hub.state_lock_time = 0
    frame(g, 1, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(160, 120))])
    assert g.hub.building_sprites, "l'auberge n'a pas été construite"
    b = next(iter(g.hub.building_sprites))
    probe = b.rect.inflate(-10, -10)
    assert b in g.obstacle_sprites.near(probe), "bâtiment absent de l'index spatial"


@test
def full_loop_runs(g):
    """La vraie boucle game.run() démarre et s'arrête proprement."""
    g.return_to_menu()
    calls = {'n': 0}
    orig = g.events

    def events():
        calls['n'] += 1
        if calls['n'] == 5:
            g.game_state = 'hub'
        if calls['n'] == 10:
            enter_dungeon(g)
        if calls['n'] == 40:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        orig()
    g.events = events
    try:
        g.run()
    except SystemExit:
        pass
    assert calls['n'] >= 40


def main():
    failures = 0
    for fn in RESULTS:
        g = Game()
        try:
            fn(g)
            _print(f"OK    {fn.__name__}")
        except Exception:
            failures += 1
            _print(f"ECHEC {fn.__name__}")
            _print(traceback.format_exc())
    _print(f"\n{len(RESULTS) - failures}/{len(RESULTS)} tests réussis")
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
