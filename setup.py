#!/usr/bin/env python3

"""
Setup file to build wheel distribution
Usage: python setup.py bdist_wheel --universal

As data_files argument dooesnt work, declare them in MANIFEST.in
this is the case for icons/*.png, benchconfig.yaml, and Qt_Style.qrc

"""

from setuptools import setup, find_packages
import setuptools
import Agiv

def find_packages():
    packages = setuptools.find_packages()
    return packages

def _main():
    print("Setup file to build wheel distribution")
    print("Usage: python setup.py bdist_wheel --universal")
    print("\n")
    setup (name = 'Agiv_Bench',
        version = Agiv.__version__,
        author  = 'Eddy LAFOND @ Apuissance3',
        packages= find_packages(),
        include_package_data= True,
        package_data= {'Agiv':['icons/*.png',
                        'benchconfig.yaml',
                        'Qt_Style.qrc']},

        package_dir= {
            'Agiv_Bench':'Agiv'
        },
        entry_points= {
            'console_scripts': [
                'agiv_start = Agiv.MainApplication:start_module_application',
                'agiv = Agiv.__main__:main'
            ]
        },
        install_requires = [
                            'pyserial>=3.5',
                            'PySide2>=5.15.2',
                            'PyYAML>=6.0',
                            'openpyxl==3.0.9',
                            ],
        description = 'Installation des sources python et dependances pour le banc de d\'etalonnage du GIV4',
        zip_safe = False
        )
    pass

if __name__ == '__main__':
    _main()


"""
data_files argument doesn't works. issue to 
"error: can't copy 'icons\led-blue-on.png': doesn't exist or not a regular file"

        data_files= [('Agiv',['icons/led-blue-on.png',
                        'led-gray.png',
                        'led-green-on.png',
                        'led-red-on.png'])],

"""