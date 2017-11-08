# Built-in modules
from os import path, pardir
import sys
import logging
import re

# not used in this stub but often useful for finding various files
PROJECT_ROOT_DIRPATH = path.join(path.dirname(__file__), pardir, pardir)
sys.path.append(PROJECT_ROOT_DIRPATH)

# Third-party modules
import click
from dotenv import find_dotenv, load_dotenv
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
# Hand-made modules
from src.models.blending import MyBlender
from src.models.stacking import MyStacker

BLEND_MODEL_INSTANCE = PLSRegression()
BLEND_MODEL_BASENAME = "layer1.PLSRegression.n_components_2"
BLEND_MODEL_PARAMS = {"n_components": 2}

LOCATIONS = (
    "ukishima",
    "ougishima",
    "yonekurayama"
)
KWARGS_READ_CSV = {
    "sep": "\t",
    "header": 0,
    "parse_dates": [0],
    "index_col": 0
}
KWARGS_TO_CSV = {
    "sep": "\t"
}


def gen_blender_and_stacker(predict_target, location):
    blend_model_name = BLEND_MODEL_BASENAME + ".{t}.{l}".format(t=predict_target, l=location)
    blender = MyBlender(BLEND_MODEL_INSTANCE, blend_model_name, BLEND_MODEL_PARAMS)

    stacker = MyStacker()
    stacker.X_train_ = stacker.get_concatenated_xgb_predict(predict_target, location)

    # 'crossval' in here is fixed in all experimental conditions
    stacker.X_train_.to_csv(
        path.join(stacker.PROCESSED_DATA_BASEPATH,
                  "dataset.predict_y.layer_0.crossval.{l}.tsv".format(l=location)),
        **KWARGS_TO_CSV
    )

    return blender, stacker


def remove_predict_target_and_location_suffix(target_string, predict_target):
    matcher = re.search(predict_target, target_string)

    return target_string[:matcher.start()-1]


@click.command()
@click.option("-t", "predict_target", flag_value="test", default=True)
@click.option("-v", "predict_target", flag_value="crossval")
@click.option("--location", "-l", type=str, default=None)
def main(predict_target, location):
    logger = logging.getLogger(__name__)
    logger.info('#0: train models')

    if location is None:
        location_list = LOCATIONS
    else:
        location_list = [location, ]

    for place in location_list:
        # get blender and stacker
        blender, stacker = gen_blender_and_stacker(predict_target, place)

        # retrieve train y
        y_true_as_train = pd.read_csv(stacker.gen_y_true_filepath(place),
                                      **KWARGS_READ_CSV)
        y_true_as_train.dropna(axis=0, inplace=True)

        logger.info('#1: get y_true @ {l} !'.format(l=place))

        # retrieve train X
        df_pred_as_train = stacker.X_train_.loc[y_true_as_train.index, ~stacker.X_train_.isnull().any()]

        logger.info('#1: get y_pred as a train data @ {l} !'.format(l=place))

        #
        # bifurcation
        #
        if predict_target == "crossval":
            # try cross-validation
            pd.DataFrame(
                blender.cross_val_predict(df_pred_as_train.values, y_true_as_train.values),
                index=df_pred_as_train.index,
                columns=[blender.model_name, ]
            ).to_csv(
                blender.gen_abspath(
                    blender.gen_serialize_filepath(
                        "predict", "{t}.{l}.tsv".format(t=predict_target, l=place))),
                **KWARGS_TO_CSV
            )

            logger.info('#2: estimate y_pred of train dataset like cross-validation @ {l} !'.format(l=place))

        elif predict_target == "test":
            # fit model with the whole samples
            blender.fit(df_pred_as_train.values, y_true_as_train.values)

            logger.info('#2: fit & serialized a model @ {l} !'.format(l=place))

            # retrieve test X
            df_pred_as_test = pd.read_csv(
                stacker.path.join(stacker.PROCESSED_DATA_BASEPATH,
                                  "predict_y.layer_0.{t}.{l}.tsv".format(t=predict_target, l=place)),
                **KWARGS_READ_CSV
            )

            logger.info('#3: get y_pred as a test data @ {l} !'.format(l=place))

            # predict
            pd.DataFrame(
                blender.predict(df_pred_as_test.as_matrix()),
                index=df_pred_as_test.index,
                columns=[remove_predict_target_and_location_suffix(blender.model_name), ]
            ).to_csv(
                blender.gen_abspath(
                    blender.gen_serialize_filepath("predict",
                                                   "{t}.{l}.tsv".format(t=predict_target, l=place))),
                **KWARGS_TO_CSV
            )

            logger.info('#4: estimate & save y_pred of test samples @ {l} !'.format(l=place))


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
