import pydub
import numpy as np
import librosa #must be version 0.9.1
import soundfile as sf
import os
import random
import shutil

# disable warnings
import warnings  
warnings.filterwarnings('ignore') 

#upload to edge-impulse-cli
os.system(r"edge-impulse-uploader --clean") #log into edge impulse

#----------------------------------------------------------------DELETE IMPORT FOLDERS-----------------------------------------------------------------------#

# Define list of paths
paths = [
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_static\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_ambiance\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_silence\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_ambiance\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_pitch\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance_pitch\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance\training",
    r"C:\Users\jnell\Downloads\Lumename\Imports\import_name\training",
]

# Loop through each path and delete its contents
for path in paths:
    print(f"Deleting contents of: {path}")
    
    # Delete all files in the directory
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

print("Deletion complete.")

#----------------------------------------------------------------NAME AUDIO MANIPULATION-----------------------------------------------------------------------#

# INITIALIZE VARIABLES/FILEPATHS:
# change to working directory

source_dir = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script'
ambiance_dir = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\ambiance'
name_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name\training"
name_pitch_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_pitch\training"
name_ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance\training"
name_ambiance_pitch_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance_pitch\training"

file_paths = []

for i in range(1, 39):
    file_paths.append(os.path.join(source_dir, f"name{i}.wav"))

#--------------------------------------------------------------------------------------#

# Ensure the target directory exists
ambiance_paths = []

# Collect all file paths in the source directory and its subdirectories
for entry in os.listdir(ambiance_dir):
    full_path = os.path.join(ambiance_dir, entry)
    # Check if it's a file and append
    if os.path.isfile(full_path):
        ambiance_paths.append(full_path)

file_path = file_paths[0]
file_name = "name1"

original_audio = pydub.AudioSegment.from_wav(file_path)

#---------------------------------------------------------------------------------#

# INITIALIZE FUNCTIONS:
# determine if audio segment is only silent
# 500 for PCM, 0.001 for floating point
def is_silent(audio_segment, threshold=500):
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
def slow_down_audio(speed_factor, file1=file_paths):
    y, sr = librosa.load(file1, sr=None)

    # Perform time-stretching
    y_slow = librosa.effects.time_stretch(y, speed_factor)

    sf.write(rf"import\temp_speed_{speed_factor}.wav", y_slow, sr)

    slow_pydub = pydub.AudioSegment.from_wav(rf"import\temp_speed_{speed_factor}.wav")

    os.remove(rf"import\temp_speed_{speed_factor}.wav")

    return find_loudest_segment(audio=slow_pydub)

# change pitch function
'''
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
'''

def change_pitch(semitone_change, file_path, target_length_ms=1000):
    # Load the audio file with librosa
    y, sr = librosa.load(file_path)
    
    # Shift the pitch
    new_y = librosa.effects.pitch_shift(y, sr, semitone_change)

    #temporary export 
    temp_path = os.path.join(source_dir, (f"temp_pitch_file.wav"))
    sf.write(temp_path, new_y, sr)
    
    shifted_audio = pydub.AudioSegment.from_wav(temp_path)

    #keep at one sec
    current_length_ms = len(shifted_audio)
    if current_length_ms < target_length_ms:
        silence_duration = target_length_ms - current_length_ms
        silence_segment = pydub.AudioSegment.silent(duration=silence_duration, frame_rate=sr)
        shifted_audio += silence_segment  # Append silence to the end of the audio
    elif current_length_ms > target_length_ms:
        shifted_audio = shifted_audio[0:target_length_ms]

    os.unlink(temp_path)

    shifted_audio = shifted_audio + ((1.5**semitone_change) + 2.5) #the more pitch change, the more volume compensation

    return shifted_audio

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
def mix_audio_files(audio1, audio2, gain_dB=0):
    # Load the audio files
    # Adjust the volume of the second audio, if needed
    if gain_dB != 0:
        audio2 += gain_dB

    # Overlay the audio files
    mixed_audio = audio1.overlay(audio2)

    # Export the mixed audio
    return mixed_audio

#loop through time shifts
def shift_looped(effect, audio, original=file_name, threshold=0.001, ambiance_audio=None, ambiance_db=None, target_dir=name_dir, label="name"):
    for i in range(1):
        # if "speed" in effect:
        #     upper_bound = 150
        #     lower_bound = -150
        # else:
        #     upper_bound = 250
        #     lower_bound = -250
        upper_bound = 300
        lower_bound = -300

        acceptable = False
        time_shift = random.randint(lower_bound,upper_bound)

        while acceptable == False:
            # modify time
            modified_audio = shift_segment(audio, time_shift, 1000)

            if is_silent(modified_audio, threshold):
                time_shift = random.randint(lower_bound,upper_bound)
                acceptable = False
            else:
                acceptable = True

        new_path = os.path.join(target_dir, (f"{label}.{original}_{effect}_shift_{time_shift}.wav"))

        return modified_audio, new_path

def rand_range(lower_bound, upper_bound, n, round_dec=2):
    range_list = []
    num = None
    for i in range(n):
        num = random.uniform(lower_bound, upper_bound)
        while num in range_list:
            num = random.uniform(lower_bound, upper_bound)
        range_list.append(round(num, round_dec))
    return range_list

def speed_up(audio, speed_factor, total_length_ms=1000):
    audio = audio.speedup(speed_factor)
    
    if len(audio) < total_length_ms:
        # Add silence at the end if the segment is too short
        padding_duration = total_length_ms - len(audio)
        end_padding = pydub.AudioSegment.silent(duration=padding_duration)
        audio += end_padding
    
    return audio

def count_files(directory):
    return len([name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name))])

#---------------------------------------------------------------------------------#

for i in range(len(file_paths)):
    file_path = file_paths[i]
    file_name = "name" + (str(i+1))
    
    original_audio = pydub.AudioSegment.from_wav(file_path)
    # MODIFY ORIGINAL_AUDIO
    original_audio = find_loudest_segment(audio=original_audio)

    for j in range(20*len(ambiance_paths)): #randomly change 30 times
        volume_change_dB = round(random.uniform(-15, 7), 2)

        semitone_change = round(random.uniform(-9, 6), 2)

        speed_factor = round(random.uniform(1, 1.4), 2)

        # Modify PITCH
        if semitone_change == 0:
            continue
        modified_audio = change_pitch(semitone_change, file_path)

        #modify SPEED
        if speed_factor == 0 or speed_factor == 1:
            continue
        elif speed_factor > 1:
            #speed up audio
            modified_audio = speed_up(modified_audio, speed_factor)
        
        #modify VOLUME
        if volume_change_dB == 0:
            continue
        modified_audio = modified_audio + volume_change_dB

        #directories: name_dir, name_pitch_dir, name_ambiance_dir, name_ambiance_pitch_dir
        if semitone_change > -5.25 and semitone_change < 2.75:
            modified_audio, new_path = shift_looped(f"volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=name_dir, label="name")
            modified_audio.export(new_path, format="wav")
        else:
            modified_audio, new_path = shift_looped(f"volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=name_pitch_dir, label="name_pitch")
            modified_audio.export(new_path, format="wav")

#---------------------------------------------------------------------------------#

    #integrate background noise 
    for ambiance_path in ambiance_paths:
        start = ambiance_path.find("\\ambiance\\")
        start += len("\\ambiance\\") #len("\\ambiance\\") = 12
        ambiance_name = ambiance_path[start:-4] #start at name, end at ".wav"

        for j in range(20): #randomly change 20 times
            ambiance_audio = pydub.AudioSegment.from_wav(ambiance_path)

            #SET RAND VARIABLES
            ambiance_db = round(random.uniform(-15, 3), 2)

            volume_change_dB = ambiance_db + round(random.uniform(0, 5), 2)

            semitone_change = round(random.uniform(-9, 6), 2)

            speed_factor = round(random.uniform(1, 1.4), 2)   

            timestamp = random.randint(0, len(ambiance_audio)-1000)
            ambiance_segment = ambiance_audio[timestamp:timestamp+1001]

            # Modify PITCH
            if semitone_change == 0:
                pass
            else:
                modified_audio = change_pitch(semitone_change, file_path)

            #modify SPEED
            if speed_factor == 0 or speed_factor == 1:
                pass
            elif speed_factor > 1:
                #speed up audio
                modified_audio = speed_up(modified_audio, speed_factor)
            
            #modify VOLUME
            if volume_change_dB == 0:
                pass
            else:
                modified_audio = modified_audio + volume_change_dB

            #directories: name_dir, name_pitch_dir, name_ambiance_dir, name_ambiance_pitch_dir
            if semitone_change > -5.25 and semitone_change < 2.75:
                modified_audio, new_path = shift_looped(f"{ambiance_name}_gain_{ambiance_db}_volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=name_ambiance_dir, label="name_ambiance")
                modified_audio = mix_audio_files(modified_audio, ambiance_segment, gain_dB=ambiance_db)
                modified_audio.export(new_path, format="wav")
            else:
                modified_audio, new_path = shift_looped(f"volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=name_ambiance_pitch_dir, label="name_ambiance_pitch")
                modified_audio = mix_audio_files(modified_audio, ambiance_segment, gain_dB=ambiance_db)
                modified_audio.export(new_path, format="wav")

print(f"(name) Moved {count_files(name_dir)} files to name_dir")
print(f"(name) Moved {count_files(name_pitch_dir)} files to name_pitch_dir")
print(f"(name) Moved {count_files(name_ambiance_dir)} files to name_ambiance_dir")
print(f"(name) Moved {count_files(name_ambiance_pitch_dir)} files to name_ambiance_pitch_dir")

#----------------------------------------------------------------STATIC MANIPULATION-----------------------------------------------------------------------#


# Define the source and target directories 
source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\static'
static_dir = r'C:\Users\jnell\Downloads\Lumename\Imports\import_static\training'

#--------------------------------------------------------------------------------------#

# Collect all file paths in the source directory and its subdirectories
static_files = []
for root, dirs, files in os.walk(source_dir):
    for file in files:
        static_files.append(os.path.join(root, file))

n = count_files(name_ambiance_dir) / 2
n = int(round(n // len(static_files)))+1

# Move each selected file to the target directory
static_counter = 0
for file_path in static_files:
    original_audio = pydub.AudioSegment.from_wav(file_path)
    for volume_change_dB in rand_range(-5, 21, n):
        static_counter += 1

        # Modify volume
        modified_audio = original_audio + volume_change_dB

        # Export the modified file
        new_path = os.path.join(static_dir, (f"static.{str(static_counter)}_{volume_change_dB}db_{os.path.basename(file_path)}"))
        modified_audio.export((new_path), format="wav")
    

print(f"(static) Moved {static_counter} files to static_dir")


#----------------------------------------------------------------BACKGROUND NOISE MANIPULATION-----------------------------------------------------------------------#

# Define the source and target directories 
source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\speech_commands_v0.02'
ambiance_source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\full_ambiance'
ambiance_source_dir2 = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\ambiance'
ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_ambiance\training"
gibberish_ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_ambiance\training"
gibberish_silence_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_silence\training"

#--------------------------------------------------------------------------------------#

# Collect all file paths in the AMBIANCE directory and its subdirectories
ambiance_files = [os.path.join(ambiance_source_dir, f) for f in os.listdir(ambiance_source_dir)]

ambiance_files.extend(os.path.join(ambiance_source_dir2, f) for f in os.listdir(ambiance_source_dir2))

ambiance_counter = 0

for file_path in ambiance_files:
    ambiance_original = pydub.AudioSegment.from_wav(file_path)
    length_audio = len(ambiance_original)
    start = 0
    one_second = 1000 # 1000 ms = 1 sec
    for i in range(0, length_audio//2, one_second):
        for j in range(4):
            ambiance_db = random.uniform(-10, 5)

            # Calculate the end position for the current segment
            end = start + one_second
            
            # Ensure the end position does not exceed the audio length
            if end <= length_audio:
                # Extract the segment
                segment = ambiance_original[start:end]
                segment = segment + ambiance_db

                try:
                    new_path = os.path.join(ambiance_dir, (f"ambiance.{str(ambiance_counter)}_{os.path.basename(file_path)}"))
                    segment.export((new_path), format="wav")
                    ambiance_counter += 1
                except Exception as e:
                    print(f"(ambiance) Error copying {file_path} to {new_path}: {e}")
            
        # Update the start position for the next segment
        start = end

print(f"(ambiance) Moved {ambiance_counter} files to ambiance_dir")

#--------------------------------------------------------------------------------------#

# Collect all file paths in the SOURCE directory and its subdirectories
all_files = []
for root, dirs, files in os.walk(source_dir):
    for file in files:
        all_files.append(os.path.join(root, file))

# Randomly select files
selected_files = random.sample(all_files, ambiance_counter)

# Move each selected file to the target directory
gibberish_ambiance_counter = 0
for file_path in selected_files:
    ambiance_path = random.choice(ambiance_files)
    
    ambiance_audio = pydub.AudioSegment.from_wav(ambiance_path)
    unknown_word = pydub.AudioSegment.from_wav(file_path)

    timestamp = random.randint(0, len(ambiance_audio)-1000)
    ambiance_segment = ambiance_audio[timestamp:timestamp+1001]

    ambiance_db = random.randint(-4, 4) 
    modified_audio = mix_audio_files(unknown_word, ambiance_segment, gain_dB=ambiance_db)

    new_path = os.path.join(gibberish_ambiance_dir, (f"gibberish_ambiance.{str(gibberish_ambiance_counter)}_ambiance_{ambiance_db}db_{os.path.basename(file_path)}"))
    modified_audio.export(new_path, format="wav")

    gibberish_ambiance_counter += 1

print(f"(gibberish_ambiance) Moved {gibberish_ambiance_counter} files to gibberish_ambiance_dir")


# Randomly select files
selected_files = random.sample(all_files, ambiance_counter)

gibberish_silence_counter = 0
for file_path in selected_files:
    new_path = os.path.join(gibberish_silence_dir, (f"gibberish_silence.{str(gibberish_silence_counter)}_{os.path.basename(file_path)}"))
    shutil.copy(file_path, new_path)
    gibberish_silence_counter += 1
    
print(f"(gibberish_silence) Moved {gibberish_silence_counter} files to gibberish_silence_dir")

#----------------------------------------------------------------UPLOAD TO EDGE IMPULSE CLI-----------------------------------------------------------------------#

#name all improt files
import_validation_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_validation"
import_static_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_static"
import_ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_ambiance"
import_gibberish_silence_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_silence"
import_gibberish_ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_gibberish_ambiance"
import_name_pitch_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_pitch"
import_name_ambiance_pitch_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance_pitch"
import_name_ambiance_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name_ambiance"
import_name_dir = r"C:\Users\jnell\Downloads\Lumename\Imports\import_name"



#upload NAME training data
os.system(rf"edge-impulse-uploader --label name --directory {import_name_dir}")

#upload NAME PITCH training data
os.system(rf"edge-impulse-uploader --label name_pitch --directory {import_name_pitch_dir}")

#upload NAME AMBIANCE training data
os.system(rf"edge-impulse-uploader --label name_ambiance --directory {import_name_ambiance_dir}")

#upload NAME AMBIANCE PITCH training data
os.system(rf"edge-impulse-uploader --label name_ambiance_pitch --directory {import_name_ambiance_pitch_dir}")



#upload STATIC training data
os.system(rf"edge-impulse-uploader --label static --directory {import_static_dir}")



#upload AMBIANCE training data
os.system(rf"edge-impulse-uploader --label ambiance --directory {import_ambiance_dir}")

#upload GIBBERISH_AMBIANCE training data
os.system(rf"edge-impulse-uploader --label gibberish_ambiance --directory {import_gibberish_ambiance_dir}")

#upload GIBBERISH_SILENCE training data
os.system(rf"edge-impulse-uploader --label gibberish_silence --directory {import_gibberish_silence_dir}")


#upload ALL TESTING data
os.system(rf"edge-impulse-uploader --directory {import_validation_dir}")

# play sound to signify end of program
os.system(r"start C:\Users\jnell\Downloads\Lumename\Other\note.wav")