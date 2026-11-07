"""Groupe de sprites avec index spatial.

Les collisions parcouraient auparavant TOUS les obstacles (≈ 8 000 murs) pour
chaque entité et chaque frame. Ce groupe range les obstacles (statiques) dans
une grille de cellules : une requête ne teste plus que les quelques murs
voisins de l'entité.
"""
import pygame


class SpatialGroup(pygame.sprite.Group):
    CELL = 128

    def __init__(self, *sprites):
        self._grid = {}
        self._cells_of = {}
        # Les sprites (Tile, Building...) s'ajoutent souvent au groupe dans
        # super().__init__(), AVANT d'avoir un rect : on les indexe plus tard.
        self._pending = []
        super().__init__(*sprites)

    # --- indexation -----------------------------------------------------
    def _cells(self, rect):
        c = self.CELL
        x0, y0 = rect.left // c, rect.top // c
        x1, y1 = (rect.right - 1) // c, (rect.bottom - 1) // c
        return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]

    def _index(self, sprite):
        cells = self._cells(sprite.rect)
        self._cells_of[sprite] = cells
        for key in cells:
            self._grid.setdefault(key, []).append(sprite)

    def _flush(self):
        if not self._pending:
            return
        pending, self._pending = self._pending, []
        for sprite in pending:
            if sprite in self._cells_of or not self.has(sprite):
                continue
            if getattr(sprite, 'rect', None) is None:
                self._pending.append(sprite)
            else:
                self._index(sprite)

    def add_internal(self, sprite, layer=None):
        super().add_internal(sprite, layer)
        self._pending.append(sprite)

    def remove_internal(self, sprite):
        super().remove_internal(sprite)
        for key in self._cells_of.pop(sprite, ()):
            bucket = self._grid.get(key)
            if bucket and sprite in bucket:
                bucket.remove(sprite)

    def empty(self):
        super().empty()
        self._grid.clear()
        self._cells_of.clear()
        self._pending.clear()

    # --- requêtes -------------------------------------------------------
    def near(self, rect, margin=8):
        """Retourne les obstacles susceptibles de toucher `rect`."""
        self._flush()
        found = []
        seen = set()
        for key in self._cells(rect.inflate(margin * 2, margin * 2)):
            for s in self._grid.get(key, ()):
                if id(s) not in seen:
                    seen.add(id(s))
                    found.append(s)
        return found


def nearby_obstacles(group, rect):
    """Helper tolérant : fonctionne avec un SpatialGroup ou un Group classique."""
    near = getattr(group, 'near', None)
    if near is not None:
        return near(rect)
    return group
