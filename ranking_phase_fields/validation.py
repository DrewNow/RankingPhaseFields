"""5-fold validation"""
import sys
import numpy as np
from ranking_phase_fields.parse_icsd import *
from ranking_phase_fields.generate_study  import *
from ranking_phase_fields.features import *
from ranking_phase_fields.models import *
# Import all models
from pyod.models.auto_encoder import AutoEncoder
from pyod.models.vae import VAE
from pyod.models.abod import ABOD
from pyod.models.feature_bagging import FeatureBagging
from pyod.models.hbos import HBOS
from pyod.models.iforest import IForest
from pyod.models.knn import KNN
from pyod.models.lof import LOF
from pyod.models.ocsvm import OCSVM
from pyod.models.pca import PCA
from pyod.models.sos import SOS
from pyod.models.lscp import LSCP
from pyod.models.cof import COF
from pyod.models.cblof import CBLOF
from pyod.models.sod import SOD
from pyod.models.loci import LOCI
from pyod.models.mcd import MCD

def validate(phase_fields, features, x_train, model, natom, average):
    """ split training data, train and validate a model"""
    ndes = len(features)
    nnet = [int(ndes*natom/2), int(ndes*natom/4), int(ndes*natom/8), int(ndes*natom/16), \
            natom, int(ndes*natom/16),  int(ndes*natom/8), int(ndes*natom/4), int(ndes*natom/2)]

    # models
    clfs = {
    'AE'             : AutoEncoder(hidden_neurons=nnet, contamination=0.1, epochs=15),
    'VAE'            : VAE(encoder_neurons=nnet[:5], decoder_neurons=nnet[4:], contamination=0.1, epochs=15),
    'ABOD'           : ABOD(),
    'FeatureBagging' : FeatureBagging(),
    'HBOS'           : HBOS(),
    'IForest'        : IForest(),
    'KNN'            : KNN(),
    'LOF'            : LOF(),
    'OCSVM'          : OCSVM(),
    'PCA'            : PCA(),
    'SOS'            : SOS(),
    'COF'            : COF(),
    'CBLOF'          : CBLOF(),
    'SOD'            : SOD(),
    'LOCI'           : LOCI(),
    'MCD'            : MCD()
    }

    clft = clfs[model]
    clf = clfs[model]
    net = vec2name(ndes, natom)
    # find threshold
    x_ = permute(x_train)
    x_ = sym2num(x_, features)
    clft.fit(x_)
    scores = np.array(clft.decision_scores_)
    threshold = 0.5 * (max(scores) + min(scores))

    print(f"Validation (5-fold) of {model} model")
    l = int(len(x_train) / 5)

    for i in range(5):
        print(f"{model} validation: {i+1} fold...")
        val_set = x_train[i*l : (i+1)*l]
        print(f"validation set size: {len(val_set)}")
        val_train = np.asarray([d for d in x_train if d not in val_set])
        print(f"training set size: {len(val_train)}")

        val_train = permute(val_train)
        val_set = permute(val_set)

        training = sym2num(val_train, features)
        val_set = sym2num(val_set, features)

        clf.fit(training)
        
        # get validation error, %
        prediction = np.asarray(clf.decision_function(val_set))
        val_error = len(prediction[prediction > threshold]) / len(val_set) * 100

        print(f"Validation error of validation set {i}: {round(val_error,2)}%", file=open('Validation_{phase_fields}_errors.dat','a'))
        thr_ar = threshold * np.ones(len(prediction))
        results = average_permutations(natom, val_set, features[0], prediction, thr_ar, net)
        getout(results, f'Validation_{phase_fields}_{model}_set{i}.csv', 'threshold')

    # if no averaging over several runs - print training scores
    if average == 1:
        train_scaled  = scale(scores)
        training_results = average_permutations(natom, x_, features[0], train_scaled, thr_ar, net)
        getout(training_results, f'{phase_fields}_{model}_training_scores.csv', 'threshold')
    return x, clft

if __name__ == "__main__":
    try:
        ffile = sys.argv[1]
    except:
        print('Provide list of elements of interest in the input file. Usage: python generate_study.py <input_file>')
        print('Reading default parameters from rpp.input')
    params = parse_input()
    training = parse_icsd(params['phase_fields'], params['anions_train'], \
            params['nanions_train'], params['cations_train'], params['icsd_file'])
    testing = generate_study(params['phase_fields'], params['elements_test'], training)
    print(f"Representing each element with {len(params['features'])} features.")
    print(f"This represents each phase fields with {numatoms(params['phase_fields'])} x {len(params['features'])} - dimensional vector.")
    print("==============================================")

    print(f"Validation the {params['method']} in 5-fold cross validation.")
    # 5-fold cross validation:
    validate(params['phase_fields'], params['features'], training, params['method'], numatoms(params['phase_fields']))
