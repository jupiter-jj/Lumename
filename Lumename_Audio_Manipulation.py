import pydub
import numpy as np
import librosa
import soundfile as sf
import os

#---------------------------------------------------------------------------------#

# INITIALIZE VARIABLES/FILEPATHS:
# change to working directory
os.chdir(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script")

file_path = r"original.wav"

original_audio = pydub.AudioSegment.from_wav(file_path)

#---------------------------------------------------------------------------------#

# INITIALIZE FUNCTIONS:
# find loudest 1 second segment (most likely when name is said)
def find_loudest_segment(audio=original_audio, spike_threshold=10, segment_length_ms=1000):
    # Get the list of loudness of each millisecond
    loudness_list = [audio[i:i+1].dBFS for i in range(len(audio))]

    # Find the first spike in volume
    for i in range(30, len(loudness_list)):
        if loudness_list[i] - loudness_list[i-1] > spike_threshold:
            start = i
            break
    else:
        # No spike found, return None or handle this case as you see fit
        return None

    # Extract the segment starting at the spike
    end = min(start + segment_length_ms, len(audio))
    return audio[start:end]

# slow down audio (USES LIBROSA)
def slow_down_audio(speed_factor):
    y, sr = librosa.load(file_path, sr=None)

    # Perform time-stretching
    y_slow = librosa.effects.time_stretch(y, speed_factor)

    sf.write(f"name_speed_{speed_factor}.wav", y_slow, sr)

    slow_pydub = pydub.AudioSegment.from_wav(f"name_speed_{speed_factor}.wav")

    return find_loudest_segment(audio=slow_pydub)

# change pitch function
def change_pitch(semitone_change, target_length_ms=1000):
    # Change the pitch
    new_sample_rate = int(original_audio.frame_rate * (2 ** (semitone_change / 12.0)))
    
    # Shift the pitch up or down
    shifted_audio = original_audio._spawn(original_audio.raw_data, overrides={'frame_rate': new_sample_rate})
    
    # Calculate the speed change ratio
    speed_change = 2 ** (-semitone_change / 12.0)

    # Adjust speed to maintain the original tempo
    shifted_audio_with_original_tempo = shifted_audio.set_frame_rate(int(shifted_audio.frame_rate * speed_change))

    # Pad with silence if the audio is shorter than the target length
    if len(shifted_audio_with_original_tempo) < target_length_ms:
        silence = pydub.AudioSegment.silent(duration=target_length_ms - len(shifted_audio_with_original_tempo))
        shifted_audio_with_original_tempo += silence

    return shifted_audio_with_original_tempo

# shift audio to be in diff places
def shift_segment(segment, shift_ms, total_length_ms):
    shifted_segment = pydub.AudioSegment.silent(duration=total_length_ms)
    insert_position = shift_ms if shift_ms > 0 else 0
    shifted_segment = shifted_segment.overlay(segment, position=insert_position)
    return shifted_segment

#---------------------------------------------------------------------------------#

# MODIFY ORIGINAL_AUDIO
original_audio = find_loudest_segment()
original_audio.export("name_original_1sec.wav", format="wav") #export the 1 sec

# adjust volume (-15dB to +15dB)
for volume_change_dB in range(-15, 16, 5):
    # Modify volume
    modified_audio = original_audio + volume_change_dB

    # Export the modified file
    modified_audio.export(f"name_volume_{volume_change_dB}.wav", format="wav")

# adjust pitch (-10 semitones to 10 semitones)
for semitone_change in range(-10, 11, 2):
    # Modify pitch
    modified_audio = change_pitch(semitone_change)

    # Save the modified audio
    modified_audio.export(f"name_pitch_{semitone_change}.wav", format="wav")

# adjust timing (-500ms to 500ms)
for time_shift in range(-250, 251, 100):
    # modify time
    modified_audio = shift_segment(original_audio, time_shift, 1000)   # Shift 0.5s to the left

    # export audio
    modified_audio.export(f"name_shift_{time_shift}.wav", format="wav")

#ONLY SPEEDS UP!
for speed_factor in np.arange(0.5, 2.1, 0.25):
    if speed_factor == 0:
        continue
    elif speed_factor > 1:
        #speed up audio
        modified_audio = original_audio.speedup(speed_factor)
    else:
        modified_audio = slow_down_audio(speed_factor)
    
    # export audio
        modified_audio.export(f"name_speed_{speed_factor}.wav", format="wav")
