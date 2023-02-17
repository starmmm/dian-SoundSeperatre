import os
import soundfile as sf
import resampy

path = "/home/cwc2022/soundSeparate/data/data_origin/archive/wavfiles"
resamplePath = "/home/cwc2022/soundSeparate/data/data_resample/bird_resample"

i = 0
resample_fs = 8000
# a = os.path.exists(path)
for root, dirs, files in os.walk(path):
    for file in files:
        wavFile = os.path.join(root, file)
        s1_16k, fs = sf.read(wavFile)
        data = resampy.resample(s1_16k, fs, resample_fs )
        mix_out_name = os.path.join(resamplePath, "resample_{}".format(file))
        sf.write(mix_out, data, resample_fs , format='WAV', subtype='PCM_16')
        i = i+1
        print(i)
