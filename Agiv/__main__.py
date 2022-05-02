from .MainApplication import start_module_application


def main():
    start_module_application()

# Permet de demarer le package avec 
#   python -m Agiv
# La declaration de ce fichier est dans la section entry_points de setup.py
if __name__ == '__main__':
    main()
