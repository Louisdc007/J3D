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
def new_mechanics(g):
    """Contrats, autels, parade des squelettes, pièges, poison, forge."""
    random.seed(5)
    enter_dungeon(g)
    p = g.player
    p.max_health = p.health = 1000
    board = g.hub.board
    board.contracts = []
    board.ensure(p.level)
    board.contracts[0] = {'kind': 'kill_any', 'goal': 1, 'progress': 0, 'target': None,
                          'desc': 'test', 'reward': {'gold': 5, 'iron': 5, 'xp': 5}}
    e = next(iter(g.attackable_sprites))
    e.health = 0
    g.on_enemy_killed_solo(e)
    assert board.done(board.contracts[0]), "le contrat n'a pas progressé"
    gold = p.inventory['gold']
    assert board.claim(0, p) and p.inventory['gold'] == gold + 5

    # autel
    from entities.props import Shrine, SpikeTrap
    sh = Shrine(p.hitbox.center, [g.visible_sprites])
    sh.buff = 'rage'
    g.shrines.append(sh)
    base = p.damage_mult
    g.try_interact()
    assert sh.used and p.has_buff('rage') and p.damage_mult > base

    # parade : un squelette de face pare souvent, le coup final passe toujours
    sk = Enemy([g.visible_sprites, g.attackable_sprites], (0, 0), g.obstacle_sprites, 'tier4')
    sk.hitbox.center = (p.hitbox.centerx + 60, p.hitbox.centery)
    sk.facing_right = False
    blocks = sum(sk.try_block(p.hitbox.center, 'atk') for _ in range(400))
    assert 80 < blocks < 250, blocks
    assert not any(sk.try_block(p.hitbox.center, 'finisher') for _ in range(50))

    # piège : blesse quand les pointes sont sorties
    trap = SpikeTrap(p.hitbox.topleft, [g.visible_sprites])
    trap.phase_i = 2
    assert trap.hurts(p.hitbox)

    # poison : fait perdre des PV au fil du temps
    p.vulnerable = True
    hp = p.health
    p.apply_poison(3)
    for _ in range(40):
        g.update_dungeon_solo(1 / 30)
    assert p.health < hp, "le poison n'inflige pas de dégâts"

    # armure : réduit les dégâts subis
    p.upgrades['armor'] = 5
    p.vulnerable = True; p.is_dashing = False
    hp = p.health
    dealt = p.get_damage(100, (0, 0))
    assert dealt == 60 and p.health == hp - 60, dealt


@test
def save_roundtrip(g):
    """Les nouveautés (contrats, forge, potions, perks) survivent à une sauvegarde."""
    p = g.player
    p.upgrades['armor'] = 2; p.potions = 4; p.perks = {'crit': 1}
    g.hub.board.ensure(3)
    descs = [c['desc'] for c in g.hub.board.contracts]
    g.save_all()
    g2 = Game()
    assert g2.player.upgrades['armor'] == 2 and g2.player.potions == 4 and g2.player.perks == {'crit': 1}
    assert [c['desc'] for c in g2.hub.board.contracts] == descs


@test
def full_loop_runs(g):
    """La vraie boucle game.run() démarre et s'arrête proprement (doit rester le dernier test :
    la sortie du jeu appelle pygame.quit())."""
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
