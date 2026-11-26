"""Illustrations. Every module in this folder can define scene classes with a WORD
attribute; get_art(word) finds the right one. To add a new word's picture, add a class
(in an existing or new module) with WORD = "<the word>", __init__() and frame(t) -> 1600x1600 RGB image."""
import importlib, pkgutil

_registry = None

def _load():
    global _registry
    _registry = {}
    for m in pkgutil.iter_modules(__path__):
        mod = importlib.import_module(f"{__name__}.{m.name}")
        for obj in vars(mod).values():
            if isinstance(obj, type) and isinstance(getattr(obj, "WORD", None), str):
                _registry[obj.WORD] = obj

def get_art(word):
    if _registry is None:
        _load()
    if word not in _registry:
        # No scene of its own (e.g. an auto-generated drawing failed its checks): use the backup scene.
        print(f"Note: no illustration for '{word}', using the backup scene (engine/art/fallback.py).")
        from engine.art.fallback import GenericScene
        return GenericScene(word)
    return _registry[word]()

def available():
    if _registry is None:
        _load()
    return sorted(_registry)
