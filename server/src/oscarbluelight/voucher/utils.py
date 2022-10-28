import importlib


def load_cls_from_abs_path(path):
    pkgname, cls_name = path.rsplit(".", 1)
    pkg = importlib.import_module(pkgname)
    return getattr(pkg, cls_name)
