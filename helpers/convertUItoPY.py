import os
from optparse import Values
from pathlib import PurePath

from PyQt5.uic.driver import Driver


def convert_ui_to_py(ui_path, py_path):
    opts = Values(defaults={
        "preview": False,
        "from_imports": False,
        "import_from": False,
        "indent": 4,
        "resource_suffix": None,
        "debug": False,
        "output": py_path,
        "execute": True,
    })
    driver = Driver(opts, ui_path)
    driver.invoke()


def convert_all_files(folder_path):
    for _, _, files in os.walk(folder_path):
        for file in files:
            convert_ui_to_py(folder_path / file, folder_path.parent / "py" / (file.split(".")[0] + ".py"))


if __name__ == '__main__':
    convert_all_files(PurePath("../interface/ui"))
