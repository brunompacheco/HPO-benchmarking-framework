import optuna
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from math import sqrt
import os
from pathlib import Path

from datasets.dummy import preprocessing as pp

###
# Preprocessing
abs_folder_path = os.path.abspath(path='datasets')
data_folder = Path(abs_folder_path)
train_file = "train.csv"
test_file = "test.csv"
submission_file = "sample_submission.csv"

train_raw = pp.load_data(data_folder, train_file)
test_raw = pp.load_data(data_folder, test_file)

X_train, y_train, X_val, y_val, X_test = pp.process(train_raw, test_raw, standardization=False, logarithmic=False,
                                                    count_encoding=False)


###

def objective(trial):
    n_est = trial.suggest_int(name='n_estimators', low=1, high=200)
    m_depth = trial.suggest_int(name='max_depth', low=1, high=80)
    max_features = trial.suggest_categorical(name='max_features', choices=['auto', 'sqrt'])

    params = {'n_estimators': n_est,
              'max_depth': m_depth,
              'max_features': max_features}

    rf = RandomForestRegressor(**params)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_val)

    loss = sqrt(mean_squared_error(y_val, y_pred))

    return loss


study = optuna.create_study()

print('Warmstart!')
study.enqueue_trial(params={'n_estimators': 100,
                            'max_depth': 40,
                            'max_features': 'auto'})

print('Optimization!')
study.optimize(func=objective, n_trials=30, n_jobs=4)
