import pydub
import numpy as np
import librosa #must be cersion 0.9.1
import soundfile as sf
import os
import random

#---------------------------------------------------------------------------------#

# INITIALIZE VARIABLES/FILEPATHS:
# change to working directory
os.chdir(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script")

file_names = []

for i in range(1, 23):
    file_names.append("name" + str(i))

ambiance_names = ["television", "traffic", "coffee2", "coffee1", "river", "wind", "birds", "rain"]

file_name = file_names[0]

original_audio = pydub.AudioSegment.from_wav(f"{file_name}.wav")

#---------------------------------------------------------------------------------#

# INITIALIZE FUNCTIONS:
# determine if audio segment is only silent
def is_silent(audio_segment, threshold=0.001):
    # Convert the audio segment to raw data
    raw_data = np.array(audio_segment.get_array_of_samples())

    # Check if all values in the array are below the threshold
    return np.all(np.abs(raw_data) < threshold)

# find loudest 1 second segment (most likely when name is said)
def find_loudest_segment(audio=original_audio, segment_length_ms=1000):
    # Initialize variables to track the loudest segment
    loudest_avg = -np.inf
    loudest_segment = None

    # Iterate over 1-second segments
    for i in range(0, (len(audio) - segment_length_ms) + 1, segment_length_ms):
        segment = audio[i:i + segment_length_ms]
        
        # Convert to numpy array for volume calculation
        segment_np = np.array(segment.get_array_of_samples())

        # Calculate average volume for this segment
        avg_volume = np.mean(np.abs(segment_np))

        # Check if this segment is louder than the current loudest
        if avg_volume > loudest_avg:
            loudest_avg = avg_volume
            loudest_segment = segment

    return loudest_segment

# slow down audio (USES LIBROSA)
def slow_down_audio(speed_factor, file1=(f"{file_name}.wav")):
    y, sr = librosa.load(file1, sr=None)

    # Perform time-stretching
    y_slow = librosa.effects.time_stretch(y, speed_factor)

    sf.write(f"name_speed_{speed_factor}.wav", y_slow, sr)

    slow_pydub = pydub.AudioSegment.from_wav(f"name_speed_{speed_factor}.wav")

    return find_loudest_segment(audio=slow_pydub)

# change pitch function
def change_pitch(semitone_change, target_length_ms=1000, audio=original_audio):
    # Change the pitch
    new_sample_rate = int(audio.frame_rate * (2 ** (semitone_change / 12.0)))
    
    # Shift the pitch up or down
    shifted_audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
    
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
    if shift_ms < 0:
        # Calculate the amount to truncate from the start of the segment
        truncate_ms = min(-shift_ms, len(segment))
        # Truncate the segment
        shifted_segment = segment[truncate_ms:]
    else:
        # Positive shift: add silence before the segment
        initial_silence = pydub.AudioSegment.silent(duration=shift_ms)
        shifted_segment = initial_silence + segment

    # Adjust the total length of the segment
    if len(shifted_segment) < total_length_ms:
        # Add silence at the end if the segment is too short
        padding_duration = total_length_ms - len(shifted_segment)
        end_padding = pydub.AudioSegment.silent(duration=padding_duration)
        shifted_segment += end_padding
    elif len(shifted_segment) > total_length_ms:
        # Truncate the segment if it is too long
        shifted_segment = shifted_segment[:total_length_ms]

    return shifted_segment

#mix two audio files
def mix_audio_files(audio1, file2_path, gain_dB=0):
    # Load the audio files
    audio2 = pydub.AudioSegment.from_file(file2_path)

    # Adjust the volume of the second audio, if needed
    if gain_dB != 0:
        audio2 += gain_dB

    # Overlay the audio files
    mixed_audio = audio1.overlay(audio2)

    # Export the mixed audio
    return mixed_audio

#loop through time shifts
def shift_looped(effect, audio, original=file_name, threshold=0.001):
    for time_shift in range(-500, 500, 500):
        if time_shift == 0:
            continue

        # modify time
        modified_audio = shift_segment(audio, time_shift, 1000)

        if is_silent(modified_audio, threshold):
            continue
        else:
            # export audio
            modified_audio.export(f"{original}_{effect}_shift_{time_shift}.wav", format="wav")

#---------------------------------------------------------------------------------#

for i in range(len(file_names)):
    file_name = file_names[i]
    original_audio = pydub.AudioSegment.from_wav(f"{file_name}.wav")
    # MODIFY ORIGINAL_AUDIO
    original_audio = find_loudest_segment(audio=original_audio)
    original_audio.export(f"{file_name}_original_1sec.wav", format="wav") #export the 1 sec

    shift_looped(f"original", original_audio, original=file_name)

    # adjust volume (-10dB to +10dB)
    for volume_change_dB in range(-10, 11, 5):
        if volume_change_dB == 0:
            continue

        # Modify volume
        modified_audio = original_audio + volume_change_dB

        # Export the modified file
        modified_audio.export(f"{file_name}_volume_{volume_change_dB}.wav", format="wav")

        shift_looped(f"volume_{volume_change_dB}", modified_audio, original=file_name)

    # adjust pitch (-10 semitones to 10 semitones)
    for semitone_change in range(-10, 11, 5):
        # Modify pitch
        modified_audio = change_pitch(semitone_change, audio=original_audio)

        # Save the modified audio
        modified_audio.export(f"{file_name}_pitch_{semitone_change}.wav", format="wav")

        shift_looped(f"pitch_{semitone_change}", modified_audio, original=file_name)

    #ONLY SPEEDS UP!
    for speed_factor in np.arange(0.5, 1.6, 0.5):
        if speed_factor == 0 or speed_factor == 1:
            continue
        elif speed_factor > 1:
            #speed up audio
            modified_audio = original_audio.speedup(speed_factor)
        else:
            modified_audio = slow_down_audio(speed_factor, file1=(f"{file_name}.wav"))
        
        # export audio
            modified_audio.export(f"{file_name}_speed_{speed_factor}.wav", format="wav")
        
        shift_looped(f"speed_{speed_factor}", modified_audio, original=file_name)

#---------------------------------------------------------------------------------#

    #integrate background noise 
    for ambiance in ambiance_names:
        ambiance_file_name = os.path.join("ambiance", f"{ambiance}.wav")

        ambiance_audio = pydub.AudioSegment.from_wav(ambiance_file_name)

        raw_ambiance = np.array(ambiance_audio.get_array_of_samples())

        threshold = np.mean(raw_ambiance) * 1.1

        mixed_audio = mix_audio_files(original_audio, ambiance_file_name)

        #export mixed audio
        mixed_audio.export(f"{file_name}_{ambiance}.wav", format="wav")

        #export mixed audio shifted
        shift_looped(f"{ambiance}", original_audio)

        # adjust volume (-10dB to +10dB)
        for volume_change_dB in range(-10, 11, 5):
            if volume_change_dB == 0:
                continue

            # Modify volume
            modified_audio = mixed_audio + volume_change_dB

            # Export the modified file
            modified_audio.export(f"{file_name}_volume_{volume_change_dB}_{ambiance}.wav", format="wav")

            shift_looped(f"volume_{volume_change_dB}_{ambiance}", modified_audio, original=file_name, threshold=threshold)

        # adjust pitch (-10 semitones to 10 semitones)
        for semitone_change in range(-10, 11, 5):
            # Modify pitch
            modified_audio = change_pitch(semitone_change, audio=mixed_audio)

            # Save the modified audio
            modified_audio.export(f"{file_name}_pitch_{semitone_change}_{ambiance}.wav", format="wav")

            shift_looped(f"pitch_{semitone_change}_{ambiance}", modified_audio, original=file_name, threshold=threshold)

        # speed and slow down
        for speed_factor in np.arange(0.5, 1.6, 0.5):
            if speed_factor == 0 or speed_factor == 1:
                continue
            elif speed_factor > 1:
                #speed up audio
                modified_audio = mixed_audio.speedup(speed_factor)
            else:
                #slow down audio
                modified_audio = slow_down_audio(speed_factor, file1=(ambiance_file_name))
            
            # export audio
            modified_audio.export(f"{file_name}_speed_{speed_factor}_{ambiance}.wav", format="wav")

            shift_looped(f"speed_{speed_factor}_{ambiance}", modified_audio, original=file_name, threshold=threshold)

#---------------------------------------------------------------------------------#
            
#delete files at random until having 2800
def delete_random_files(directory, desired_count, keep_list):
    # List all files in the directory
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    desired_count += len(keep_list) + 2 #2 stands for amt of python files inside
    
    # Check if the current number of files is more than the desired count
    while len(files) > desired_count:
        # Select a random file to delete
        file_to_delete = random.choice(files)

        _, file_extension = os.path.splitext(file_to_delete)

        while (file_to_delete in keep_list) or (file_extension.lower() == ".py"):
            file_to_delete = random.choice(files)
            _, file_extension = os.path.splitext(file_to_delete)
        # Delete the file
        os.remove(os.path.join(directory, file_to_delete))
        # Remove the deleted file from the list
        files.remove(file_to_delete)
        #print(f"Deleted {file_to_delete}")

    print(f"Operation completed. {len(files)} files remaining.")

delete_random_files(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script", 1600, [name + ".wav" for name in file_names])