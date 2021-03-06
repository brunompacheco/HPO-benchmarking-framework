from hyperopt import fmin, tpe, hp, Trials, STATUS_OK, STATUS_FAIL
from hyperopt.mongoexp import MongoTrials
import skopt
import numpy as np
import time
from multiprocessing import Process

from hpo_framework.baseoptimizer import BaseOptimizer
from hpo_framework.results import TuningResult
from hpo_framework import multiproc_target_funcs


class HyperoptOptimizer(BaseOptimizer):
    def __init__(self, hp_space, hpo_method, ml_algorithm, x_train, x_val, y_train, y_val, metric, n_func_evals,
                 random_seed, n_workers):
        super().__init__(hp_space, hpo_method, ml_algorithm, x_train, x_val, y_train, y_val, metric, n_func_evals,
                         random_seed, n_workers)

    def optimize(self) -> TuningResult:
        """
        Method performs a hyperparameter optimization run according to the selected HPO-method.
        :return: result: TuningResult
            TuningResult-object that contains the results of this optimization run.
        """

        # Select the specified HPO-tuning method
        if self.hpo_method == 'TPE':
            this_optimizer = tpe.suggest  # (seed=self.random_seed)

        else:
            raise Exception('Unknown HPO-method!')

        # Transform the skopt hp_space into an hyperopt space
        hyperopt_space = {}
        for i in range(len(self.hp_space)):
            if type(self.hp_space[i]) == skopt.space.space.Integer:
                hyperopt_space[self.hp_space[i].name] = hp.choice(self.hp_space[i].name,
                                                                  range(self.hp_space[i].low,
                                                                        self.hp_space[i].high + 1))

            elif type(self.hp_space[i]) == skopt.space.space.Categorical:
                hyperopt_space[self.hp_space[i].name] = hp.choice(self.hp_space[i].name,
                                                                  list(self.hp_space[i].categories))

            elif type(self.hp_space[i]) == skopt.space.space.Real:
                hyperopt_space[self.hp_space[i].name] = hp.uniform(self.hp_space[i].name,
                                                                   low=self.hp_space[i].low,
                                                                   high=self.hp_space[i].high)

            else:
                raise Exception('The skopt HP-space could not be converted correctly!')

        # Set the random seed of the random number generator
        rand_num_generator = np.random.RandomState(seed=self.random_seed)

        # Optimize on the predefined n_func_evals and measure the wall clock times
        start_time = time.time()
        self.times = []  # Initialize a list for saving the wall clock times

        if self.n_workers == 1:
            # Initialize a trial instance
            trials = Trials()

            # Start the optimization
            try:
                res = fmin(fn=self.objective, space=hyperopt_space, trials=trials, algo=this_optimizer,
                           max_evals=self.n_func_evals, rstate=rand_num_generator)
                run_successful = True

            # Algorithm crashed
            except:
                # Add a warning here
                run_successful = False

        else:
            raise Exception('Parallelization not implemented for hyperopt framework.')

        # >>>>>>>>>>>
        # ATTEMPT TO PARALELLIZE HYPEROPT VIA MONGODB >>> problems to access the trials results
        # # No parallelization
        # if self.n_workers == 1:
        #
        #     # Initialize a trial instance
        #     trials = Trials()
        #
        #     # Start the optimization
        #     try:
        #         res = fmin(fn=self.objective, space=hyperopt_space, trials=trials, algo=this_optimizer,
        #                    max_evals=self.n_func_evals, rstate=rand_num_generator)
        #         run_successful = True
        #
        #     # Algorithm crashed
        #     except:
        #         # Add a warning here
        #         run_successful = False
        #
        # # Parallelization -> use multiprocessing
        # else:
        #     try:
        #         processes = []
        #         for i in range(self.n_workers + 1):
        #
        #             if i == 0:
        #                 # >>> USE UNIQUE EXPERIMENT ID FOR EACH TRIAL
        #                 trials = MongoTrials('mongo://localhost:27017/mongo_hpo/jobs', exp_key='exp104')
        #                 p = Process(target=multiproc_target_funcs.hyperopt_target1,
        #                             args=(self.objective, hyperopt_space, trials, this_optimizer, self.n_func_evals,
        #                                   rand_num_generator))
        #             else:
        #                 p = Process(target=multiproc_target_funcs.hyperopt_target2)
        #
        #             p.start()
        #             processes.append(p)
        #
        #         for p in processes:
        #             p.join()
        #
        #         run_successful = True
        #
        #     except:
        #         run_successful = False
        # >>>>>>>>>>>

        # If the optimization run was successful, determine the optimization results
        if run_successful:

            # Determine the timestamps for each evaluation of the blackbox-function
            for i in range(len(trials.trials)):
                # Subtract the start time to receive the wall clock time of each function evaluation
                this_trial = trials.trials[i]
                this_eval_time = this_trial['result']['eval_time']
                self.times[i] = this_eval_time - start_time
            wall_clock_time = max(self.times)

            # Timestamps
            timestamps = self.times

            # Number the evaluations / iterations of this run
            evaluation_ids = list(range(1, len(trials.tids) + 1))

            # Loss of each iteration
            losses = []
            for this_result in trials.results:
                losses.append(this_result['loss'])

            # Best loss
            best_loss = min(losses)

            # Determine the best HP-configuration of this run
            best_configuration = {}
            for i in range(len(self.hp_space)):

                if type(self.hp_space[i]) == skopt.space.space.Categorical:
                    # Hyperopt only returns indexes for categorical hyperparameters
                    categories = self.hp_space[i].categories
                    # cat_idx = res[self.hp_space[i].name]
                    cat_idx = trials.best_trial['misc']['vals'][self.hp_space[i].name][0]
                    best_configuration[self.hp_space[i].name] = categories[cat_idx]

                else:
                    # best_configuration[self.hp_space[i].name] = res[self.hp_space[i].name]
                    best_configuration[self.hp_space[i].name] = \
                        trials.best_trial['misc']['vals'][self.hp_space[i].name][0]

            # HP-configuration of each iteration
            configurations = ()
            for trial in trials.trials:
                this_config = {}
                for i in range(len(self.hp_space)):

                    if type(self.hp_space[i]) == skopt.space.space.Categorical:
                        # Hyperopt only returns indexes for categorical hyperparameters
                        categories = self.hp_space[i].categories
                        cat_idx = trial['misc']['vals'][self.hp_space[i].name][0]
                        this_config[self.hp_space[i].name] = categories[cat_idx]
                    else:
                        this_config[self.hp_space[i].name] = trial['misc']['vals'][self.hp_space[i].name][0]

                configurations = configurations + (this_config,)

        # Run not successful (algorithm crashed)
        else:
            evaluation_ids, timestamps, losses, configurations, best_loss, best_configuration, wall_clock_time = \
                self.impute_results_for_crash()

        # Pass the results to a TuningResult-object
        result = TuningResult(evaluation_ids=evaluation_ids, timestamps=timestamps, losses=losses,
                              configurations=configurations, best_loss=best_loss, best_configuration=best_configuration,
                              wall_clock_time=wall_clock_time, successful=run_successful)

        return result

    def objective(self, params):
        """
        Objective function: This method passes the given hyperparameters to the ML-model for training and evaluation
        and returns the validation loss.
        :param params: dict
            Hyperparameter configuration that has been selected by the HPO-method for this iteration.
        :return: dict
            Dictionary that contains the validation loss, the optimization status and the evaluation time
        """
        # Select the corresponding objective function of the ML-Algorithm
        if self.ml_algorithm == 'RandomForestRegressor' or self.ml_algorithm == 'SVR' or \
                self.ml_algorithm == 'AdaBoostRegressor' or self.ml_algorithm == 'DecisionTreeRegressor' or \
                self.ml_algorithm == 'LinearRegression' or self.ml_algorithm == 'KNNRegressor':

            eval_func = self.train_evaluate_scikit_regressor

        elif self.ml_algorithm == 'KerasRegressor':
            eval_func = self.train_evaluate_keras_regressor

        elif self.ml_algorithm == 'XGBoostRegressor':
            eval_func = self.train_evaluate_xgboost_regressor

        else:
            raise Exception('Unknown ML-algorithm!')

        try:
            val_loss = eval_func(params=params)
            status = STATUS_OK
        except:
            status = STATUS_FAIL
            val_loss = float('nan')

        return {'loss': val_loss,
                'status': status,
                'eval_time': time.time()}
