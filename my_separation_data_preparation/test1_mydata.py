import os
import random
import numpy as np
import argparse
import logging
import soundfile as sf


def CreateFiles(input_dir_transformer, input_dir_bird, output_dir, nums_file, state):
    wavList_transformer = []
    wavList_bird = []
    mix_files = os.path.join(output_dir, 'mix_files')
    if not os.path.exists(mix_files):
        os.mkdir(mix_files)

    for root, _, files in os.walk(input_dir_transformer):
        for file in files:
            if state.upper() in root.upper() and file.endswith('WAV') or file.endswith('wav'):
                wavFile = os.path.join(root, file)
                data, sr = sf.read(wavFile)
                if len(data.shape) != 1:
                    raise ValueError
                if data.shape[0] < 10000:
                    pass
                else:
                    wavList_transformer.append(wavFile)
    random.shuffle(wavList_transformer)

    for root, _, files in os.walk(input_dir_bird):
        for file in files:
            if state.upper() in root.upper() and file.endswith('WAV') or file.endswith('wav'):
                wavFile = os.path.join(root, file)
                data, sr = sf.read(wavFile)
                if len(data.shape) != 1:
                    raise ValueError
                if data.shape[0] < 10000:
                    pass
                else:
                    wavList_bird.append(wavFile)
    random.shuffle(wavList_bird)

    if state.upper() == 'TRAIN':

        existed_list_tr = []
        existed_list_cv = []

        wavList_transformer_tr = wavList_transformer[:len(
            wavList_transformer)-int(len(wavList_transformer)*0.1)]
        wavList_transformer_cv = wavList_transformer[len(
            wavList_transformer)-int(len(wavList_transformer)*0.1):]

        wavList_bird_tr = wavList_bird[:len(
            wavList_bird)-int(len(wavList_bird)*0.1)]
        wavList_bird_cv = wavList_bird[len(
            wavList_bird)-int(len(wavList_bird)*0.1):]

        tr_file = os.path.join(mix_files, 'tr.txt')
        cv_file = os.path.join(mix_files, 'cv.txt')
        res_tr_list = []
        res_cv_list = []

        with open(tr_file, 'w') as ftr:
            for i in range(nums_file):
                mix_0 = random.sample(wavList_transformer_tr, 1)
                mix_1 = random.sample(wavList_bird_tr, 1)
                mix = [mix_0[0], mix_1[0]]
                if mix not in existed_list_tr:
                    res_tr_list.append(mix)
                else:
                    while mix in existed_list_tr:
                        mix_0 = random.sample(wavList_transformer_tr, 1)
                        mix_1 = random.sample(wavList_bird_tr, 1)
                        mix = [mix_0[0], mix_1[0]]
                res_tr_list.append(mix)
                existed_list_tr.append(mix)
                snr = np.random.uniform(0, 2.5)
                line = "{} {} {} {}\n".format(
                    mix_0[0], snr, mix_1[0], -snr)  # 会不会实际情况是变电站声音一直比鸟声大？？？
                ftr.write(line)
        ftr.close()
        with open(cv_file, 'w') as fcv:
            for i in range(int(nums_file * 0.1)):
                mix_0 = random.sample(wavList_transformer_cv, 1)
                mix_1 = random.sample(wavList_bird_cv, 1)
                mix = [mix_0[0], mix_1[0]]
                if mix not in existed_list_cv:
                    res_cv_list.append(mix)
                else:
                    while mix in existed_list_cv:
                        mix_0 = random.sample(wavList_transformer_cv, 1)
                        mix_1 = random.sample(wavList_bird_cv, 1)
                        mix = [mix_0[0], mix_1[0]]
                res_cv_list.append(mix)
                existed_list_cv.append(mix)
                snr = np.random.uniform(0, 2.5)
                line = "{} {} {} {}\n".format(mix_0[0], snr, mix_1[0], -snr)
                fcv.write(line)
        fcv.close()
    elif state.upper() == 'TEST':
        existed_list_tt = []
        wavList_transformer_tt = wavList_transformer
        wavList_bird_tt = wavList_bird
        tt_file = os.path.join(mix_files, 'tt.txt')
        res_tt_list = []
        with open(tt_file, "w") as ftt:
            for i in range(1000):
                mix_0 = random.sample(wavList_transformer_tt, 1)
                mix_1 = random.sample(wavList_bird_tt, 1)
                mix = [mix_0[0], mix_1[0]]
                if mix not in existed_list_tt:
                    res_tt_list.append(mix)
                else:
                    while mix in existed_list_tt:
                        mix_0 = random.sample(wavList_transformer_tt, 1)
                        mix_1 = random.sample(wavList_bird_tt, 1)
                        mix = [mix_0[0], mix_1[0]]
                res_tt_list.append(mix)
                existed_list_tt.append(mix)
                snr = np.random.uniform(0, 2.5)
                line = "{} {} {} {}\n".format(mix_0[0], snr, mix_1[0], -snr)
                ftt.write(line)
        ftt.close()


if __name__ == '__main__':
    # input_dir = "D:\\study\\dian_project\\sound_separate\\dataset_test\\test"
    output_dir = "D:\\study\\dian_project\\sound_separate\\dataset\\dataset_mix2"
    state = "test"
    nums_file = 100
    input_dir_transformer = "D:\\study\\dian_project\\sound_separate\\dataset\\dataset_transformer_resample"
    input_dir_bird = "D:\\study\\dian_project\\sound_separate\\dataset\\birdsong_resample"
    CreateFiles(input_dir_transformer, input_dir_bird,
                output_dir, nums_file, state)
    print(1)
