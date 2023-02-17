import os
import random
import numpy as np
import argparse
import logging
import soundfile as sf
from activlev import activlev
import tqdm
from test1_mydata import CreateFiles
from test2_mydata import GenerateMixAudio
from test3_mydata import GenrateCroValScp, GenrateTestScp, GenrateTrainScp


if __name__ == '__main__':
    output_dir = "/home/cwc2022/soundSeparate/data/dataset_fs8000"
    state = "train"
    nums_file = 10000
    useActive = False
    input_dir_transformer = "/home/cwc2022/soundSeparate/data/data_resample/transformer_resample"
    input_dir_bird = "/home/cwc2022/soundSeparate/data/data_resample/bird_resample"
    CreateFiles(input_dir_transformer, input_dir_bird,
                output_dir, nums_file, state)
    print("create file down")
    dataPath = "/home/cwc2022/soundSeparate/data/dataset_fs8000"
    GenerateMixAudio(dataPath, state, useActive)
    print("Generate MixAudio down")
    state = "test"
    CreateFiles(input_dir_transformer, input_dir_bird,
                output_dir, nums_file, state)
    print("create file down")
    GenerateMixAudio(dataPath, state, useActive)
    print("Generate MixAudio down")
    GenrateTrainScp(dataPath)
    GenrateTestScp(dataPath)
    GenrateCroValScp(dataPath)
    print("all done")
