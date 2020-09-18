class TuningResult():
    def __init__(self, evaluation_ids: list, timestamps: list, losses: list, configurations: tuple, best_loss: float,
                 best_configuration: dict):
        self.evaluation_ids = evaluation_ids  # list
        self.timestamps = timestamps  # list
        self.losses = losses  # list
        self.configurations = configurations  # tuple of dictionaries
        self.best_loss = best_loss  # float
        self.best_configuration = best_configuration  # dictionary
