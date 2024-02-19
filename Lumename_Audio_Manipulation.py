import pydub
import numpy as np
import librosa #must be version 0.9.1
import soundfile as sf
import os
import random
import shutil
import soundfile

# disable warnings
import warnings  
warnings.filterwarnings('ignore') 

#----------------------------------------------------------------DELETE IMPORT FOLDERS-----------------------------------------------------------------------#

# Define list of paths
paths = [
    r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\import\training",
    r"C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\validation\import\testing",
    r"C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\static\import\training",
    r"C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\import_unknown\training"
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
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

print("Deletion complete.")

#----------------------------------------------------------------MARK AUDIO MANIPULATION-----------------------------------------------------------------------#

# INITIALIZE VARIABLES/FILEPATHS:
# change to working directory
os.chdir(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script")

file_names = []

for i in range(1, 39):
    file_names.append("name" + str(i))

source_dir = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script'
ambiance_dir = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\ambiance'
target_dir = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\import\training'

#--------------------------------------------------------------------------------------#

# Ensure the target directory exists
os.makedirs(target_dir, exist_ok=True)
ambiance_paths = []

# Collect all file paths in the source directory and its subdirectories
for entry in os.listdir(ambiance_dir):
    full_path = os.path.join(ambiance_dir, entry)
    # Check if it's a file and append
    if os.path.isfile(full_path):
        ambiance_paths.append(full_path)

file_name = file_names[0]

original_audio = pydub.AudioSegment.from_wav(f"{file_name}.wav")

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
def slow_down_audio(speed_factor, file1=(f"{file_name}.wav")):
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

    temp_path = os.path.join(target_dir, (f"temp_pith_file.wav"))
    soundfile.write(temp_path, new_y, sr)
    
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
def shift_looped(effect, audio, original=file_name, threshold=0.001, ambiance_audio=None, ambiance_db=None, target_dir=target_dir):
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

        new_path = os.path.join(target_dir, (f"name.{original}_{effect}_shift_{time_shift}.wav"))

        return modified_audio, new_path

        #if ambiance_audio != None:
        #    modified_audio = mix_audio_files(modified_audio, ambiance_audio, gain_dB=ambiance_db)

        #new_path = os.path.join(target_dir, (f"name.{original}_{effect}_shift_{time_shift}.wav"))

        # export audio
        #modified_audio.export(new_path, format="wav")

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


#---------------------------------------------------------------------------------#

for i in range(len(file_names)):
    os.chdir(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script")
    file_name = file_names[i]
    original_audio = pydub.AudioSegment.from_wav(f"{file_name}.wav")
    # MODIFY ORIGINAL_AUDIO
    original_audio = find_loudest_segment(audio=original_audio)
    #original_audio.export(rf"import\training\name.{file_name}_original_1sec.wav", format="wav") #export the 1 sec

    for j in range(20): #randomly change 7 times
        volume_change_dB = random.uniform(-7, 7)

        semitone_change = random.uniform(-6, 6)

        speed_factor = random.uniform(1, 1.4)

        # Modify PITCH
        if semitone_change == 0:
            continue
        modified_audio = change_pitch(semitone_change, f"{file_name}.wav")

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

        #modify SHIFT
        modified_audio, new_path = shift_looped(f"volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=target_dir)

        modified_audio.export(new_path, format="wav")

#---------------------------------------------------------------------------------#

    #integrate background noise 
    for ambiance_path in ambiance_paths:
        start = ambiance_path.find("\\ambiance\\")
        start += len("\\ambiance\\") #len("\\ambiance\\") = 12
        ambiance_name = ambiance_path[start:]

        for j in range(20): #randomly change 7 times
            ambiance_audio = pydub.AudioSegment.from_wav(ambiance_path)

            #SET RAND VARIABLES
            ambiance_db = random.randint(-7, 7) 

            volume_change_dB = ambiance_db + random.uniform(2, 5)

            semitone_change = random.uniform(-7, 7)

            speed_factor = random.uniform(1, 1.4)     

            ambiance_db = random.randint(-7, 7)   

            timestamp = random.randint(0, len(ambiance_audio)-1000)
            ambiance_segment = ambiance_audio[timestamp:timestamp+1001]

            # Modify PITCH
            if semitone_change == 0:
                continue
            modified_audio = change_pitch(semitone_change, f"{file_name}.wav")

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

            #modify SHIFT
            modified_audio, new_path = shift_looped(f"{ambiance_name}_{ambiance_db}_volume_{volume_change_dB}_speed_{speed_factor}_pitch_{semitone_change}", modified_audio, original=file_name, target_dir=target_dir)

            modified_audio = mix_audio_files(modified_audio, ambiance_segment, gain_dB=ambiance_db)

            modified_audio.export(new_path, format="wav")

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

#delete_random_files(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\import", 20200, [name + ".wav" for name in file_names])

#----------------------------------------------------------------VALIDATION SET-----------------------------------------------------------------------#

#reset directory
os.chdir(os.path.expanduser('~'))

# Define the source and target directories 
source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\validation'
target_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\validation\import\testing'

#--------------------------------------------------------------------------------------#

# Ensure the target directory exists
os.makedirs(target_dir, exist_ok=True)

# Collect all file paths in the source directory and its subdirectories
all_files = []
for entry in os.listdir(source_dir):
    full_path = os.path.join(source_dir, entry)
    # Check if it's a file and append
    if os.path.isfile(full_path):
        all_files.append(full_path)


counter = 0
for file_path in all_files:
    try:
        audio = pydub.AudioSegment.from_wav(file_path)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    length_audio = len(audio)
    start = 0
    batch_size = 250
    one_second = 1000 # 1000 ms = 1 sec
    for i in range(0, length_audio, batch_size):
        for j in range(3):
            volume_change_dB = random.uniform(-7,7)
            # Calculate the end position for the current segment
            end = start + one_second
            
            # Ensure the end position does not exceed the audio length
            if end <= length_audio:
                # Extract the segment
                segment = audio[start:end]
                try:
                    new_path = os.path.join(target_dir, (f"{os.path.basename(file_path)[0:-4]}_{volume_change_dB}db_ambiance_{str(counter)}.wav"))
                    segment = segment + volume_change_dB
                    segment.export((new_path), format="wav")
                    counter += 1
                except Exception as e:
                    print(f"(ambiance) Error copying {file_path} to {new_path}: {e}")
            
        # Update the start position for the next segment
        start = end

print(f"(ambiance) Moved {counter} files to {target_dir}")

#----------------------------------------------------------------STATIC MANIPULATION-----------------------------------------------------------------------#


# Define the source and target directories 
source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\static'
target_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\static\import\training'

#--------------------------------------------------------------------------------------#

# Ensure the target directory exists
os.makedirs(target_dir, exist_ok=True)

# Collect all file paths in the source directory and its subdirectories
all_files = []
for root, dirs, files in os.walk(source_dir):
    for file in files:
        all_files.append(os.path.join(root, file))

# Move each selected file to the target directory
counter = 0
for file_path in all_files:
    original_audio = pydub.AudioSegment.from_wav(file_path)
    for volume_change_dB in rand_range(-5, 21, 5):
        counter += 1

        # Modify volume
        modified_audio = original_audio + volume_change_dB

        # Export the modified file
        new_path = os.path.join(target_dir, (f"static.{volume_change_dB}db_{(os.path.basename(file_path))[0:-2]}_{str(counter)}.wav"))
        modified_audio.export((new_path), format="wav")
    

print(f"Moved {counter} files to {target_dir}")


#----------------------------------------------------------------BACKGROUND NOISE MANIPULATION-----------------------------------------------------------------------#

def count_files(directory):
    """Counts the number of files in the given directory."""
    return len([name for name in os.listdir(directory) if os.path.isfile(os.path.join(directory, name))])

# Define the source and target directories 
source_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\speech_commands_v0.02'
ambiance_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\full_ambiance'
ambiance_dir2 = r'C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\ambiance'
target_dir = r'C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\import_unknown\training'

# Define the number of files to randomly select
x = round(count_files(r"C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\import\training")*1.1) # number of name files

#--------------------------------------------------------------------------------------#

# Collect all file paths in the AMBIANCE directory and its subdirectories
ambiance_files = [os.path.join(ambiance_dir, f) for f in os.listdir(ambiance_dir)]

ambiance_files.extend(os.path.join(ambiance_dir2, f) for f in os.listdir(ambiance_dir2))

ambiance_counter = 0
for file_path in ambiance_files:
    try:
        ambiance_original = pydub.AudioSegment.from_wav(file_path)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    length_audio = len(ambiance_original)
    start = 0
    one_second = 1000 # 1000 ms = 1 sec
    for i in range(0, length_audio, one_second):
        # Calculate the end position for the current segment
        end = start + one_second
        
        # Ensure the end position does not exceed the audio length
        if end <= length_audio:
            # Extract the segment
            segment = ambiance_original[start:end]
            try:
                new_path = os.path.join(target_dir, (f"unknown.ambiance_{str(ambiance_counter)}_{os.path.basename(file_path)}"))
                segment.export((new_path), format="wav")
                ambiance_counter += 1
            except Exception as e:
                print(f"(ambiance) Error copying {file_path} to {new_path}: {e}")
        
        # Update the start position for the next segment
        start = end

print(f"(ambiance) Moved {ambiance_counter} files to {target_dir}")

#--------------------------------------------------------------------------------------#

# Ensure the target directory exists
os.makedirs(target_dir, exist_ok=True)

# Collect all file paths in the SOURCE directory and its subdirectories
all_files = []
for root, dirs, files in os.walk(source_dir):
    for file in files:
        all_files.append(os.path.join(root, file))

# Ensure x does not exceed the number of files available
x -= ambiance_counter

# Randomly select x files
selected_files = random.sample(all_files, x)

print(f"(other) Total files available: {len(all_files)}")
print(f"(other) Files to be processed: {len(selected_files)}")

# Move each selected file to the target directory
counter = 0
for file_path in selected_files:
    try:
        new_path = os.path.join(target_dir, (f"unknown.{str(counter)}_{os.path.basename(file_path)}"))
        shutil.copy(file_path, new_path)
        counter += 1
    except Exception as e:
        print(f"(other) Error copying {file_path} to {new_path}: {e}")

print(f"(other) Moved {counter+ambiance_counter} files to {target_dir}")

#----------------------------------------------------------------UPLOAD TO EDGE IMPULSE CLI-----------------------------------------------------------------------#


#upload to edge-impulse-cli
#os.system("pip install nodejs") #pip install nodejs if needed
#os.system("npm install -g edge-impulse-cli --force") #install edge-impulse-cli if needed

os.system(r"edge-impulse-uploader --api-key ei_8d4f08d9d3c210ba69d9e71cda762768df24faee23b8f2b4ec6ce2362b57cf02") #makes data automatically go to specific project

#upload MARK training data
os.system(r"edge-impulse-uploader --label name --directory C:\Users\jnell\Downloads\Lumename\Python_Audio_Script\import")

#upload STATIC training data
os.system(r"edge-impulse-uploader --label static --directory C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\static\import")

#upload UNKNOWN training data
os.system(r"edge-impulse-uploader --label unknown --directory C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\import_unknown")

#upload ALL TESTING data
os.system(r"edge-impulse-uploader --directory C:\Users\jnell\Downloads\Lumename\Local_Training_Scripts\validation\import")