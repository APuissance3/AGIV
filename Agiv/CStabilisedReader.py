import time
import statistics

class CStabilizedReader:
    def __init__(self, interval=0.1, stability_duration=2, init_duration=1):
        """
        Args:
            interval: Intervalle entre chaque lecture (en secondes).
            stability_duration: Temps minimum pendant lequel les mesures doivent rester stables.
            init_duration: Temps d'analyse initial pour estimer la tolérance (en secondes).
        """
        self.interval = interval
        self.stability_duration = stability_duration
        self.init_duration = init_duration
        self.dynamic_threshold = None  # Seuil dynamique ajusté après la phase initiale

    def initialize_threshold(self, read_function, param=None):
        """Calcule un seuil basé sur les variations initiales."""
        initial_values = []
        end_time = time.time() + self.init_duration
        while time.time() < end_time:
            value = read_function(param) if param else read_function()
            initial_values.append(value)
            time.sleep(self.interval)

        # Calcul de l'écart type initial
        std_dev = statistics.stdev(initial_values) if len(initial_values) > 1 else 0
        self.dynamic_threshold = std_dev * 2  # Exemple : seuil basé sur 2 écarts types
        print(f"Seuil dynamique initialisé à : {self.dynamic_threshold:.2f}")

    def get_stabilized_value(self, read_function, param=None):
        """
        Lit les valeurs de l'appareil jusqu'à stabilisation.

        Args:
            read_function: Fonction de lecture (par ex., appareil.readvalue()).
            param: Paramètre optionnel pour la fonction de lecture.

        Returns:
            tuple: Moyenne et écart type des valeurs stabilisées.
        """
        # Initialisation du seuil dynamique
        if self.dynamic_threshold is None:
            self.initialize_threshold(read_function, param)

        stable_values = []
        start_stable_time = None

        while True:
            value = read_function(param) if param else read_function()
            print(f"Nouvelle mesure : {value}")

            # Ajouter la nouvelle mesure
            stable_values.append(value)

            # Vérifier si les valeurs sont dans la plage de stabilisation
            min_val, max_val = min(stable_values), max(stable_values)
            if max_val - min_val <= self.dynamic_threshold:
                if start_stable_time is None:
                    start_stable_time = time.time()
                
                # Vérifier si la durée de stabilisation est atteinte
                if time.time() - start_stable_time >= self.stability_duration:
                    mean = statistics.mean(stable_values)
                    stdev = statistics.stdev(stable_values) if len(stable_values) > 1 else 0
                    return mean, stdev
            else:
                # Réinitialiser si les valeurs ne sont pas stables
                stable_values = [value]
                start_stable_time = None
            
            time.sleep(self.interval)
