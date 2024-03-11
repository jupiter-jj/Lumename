/* Edge Impulse ingestion SDK
 * Copyright (c) 2022 EdgeImpulse Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

// If your target is limited in memory remove this macro to save 10K RAM
#define EIDSP_QUANTIZE_FILTERBANK   0

/**
 * Define the number of slices per model window. E.g. a model window of 1000 ms
 * with slices per model window set to 4. Results in a slice size of 250 ms.
 * For more info: https://docs.edgeimpulse.com/docs/continuous-audio-sampling
 */
#define EI_CLASSIFIER_SLICES_PER_MODEL_WINDOW 4

/*
 ** NOTE: If you run into TFLite arena allocation issue.
 **
 ** This may be due to may dynamic memory fragmentation.
 ** Try defining "-DEI_CLASSIFIER_ALLOCATION_STATIC" in boards.local.txt (create
 ** if it doesn't exist) and copy this file to
 ** `<ARDUINO_CORE_INSTALL_PATH>/arduino/hardware/<mbed_core>/<core_version>/`.
 **
 ** See
 ** (https://support.arduino.cc/hc/en-us/articles/360012076960-Where-are-the-installed-cores-located-)
 ** to find where Arduino installs cores on your machine.
 **
 ** If the problem persists then there's not enough memory for this model and application.
 */

/* Includes ---------------------------------------------------------------- */
#include <PDM.h>
#include <lumename-debug-1_inferencing.h>

//include for OLED
#include <DS3231.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

//Display configuration
#define SCREEN_WIDTH 128 // OLED display width, in pixels
#define SCREEN_HEIGHT 64 // OLED display height, in pixels
#define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

//RTC configuration
DS3231 myRTC;
bool century = false;
bool h12Flag;
bool pmFlag;
byte alarmDay, alarmHour, alarmMinute, alarmSecond, alarmBits;
bool alarmDy, alarmH12Flag, alarmPmFlag;

//electronic devices
#define VBR1 3
#define VBR2 4
//#define VBR3 5
//#define VBR4 6
#define LED 2 
#define KEY 7

//class indexes
#define NAME_INDEX 3
#define NAME_PITCH_INDEX 4
#define NAME_AMBIANCE_INDEX 5
#define NAME_AMBIANCE_PITCH_INDEX 6

#define STATIC_INDEX 7

//thresholds
#define MASTER_NAME_THRESHOLD 0.7
//#define AVG2_NAME_THRESHOLD 0.6
//#define DEPENDENT_NAME_THRESHOLD 0.3
//#define STATIC_THRESHOLD 0.2
//#define UNKNOWN_THRESHOLD 0.6

//debug
#define DEBUG
#define DEBUG_PRED
#define DEBUG_AVG

unsigned long currentTime = 0;
unsigned long triggerTime = 0;

float name_val_total;
float avg;
float prev;

float prev_max;
float max;
int prev_index;
int index;

/** Audio buffers, pointers and selectors */
typedef struct {
    signed short *buffers[2];
    unsigned char buf_select;
    unsigned char buf_ready;
    unsigned int buf_count;
    unsigned int n_samples;
} inference_t;

static inference_t inference;
static bool record_ready = false;
static signed short *sampleBuffer;
static bool debug_nn = false; // Set this to true to see e.g. features generated from the raw signal
static int print_results = -(EI_CLASSIFIER_SLICES_PER_MODEL_WINDOW);

/**
 * @brief      Arduino setup function
 */
void setup()
{
  digitalWrite(LED_PWR, LOW);
  digitalWrite(PIN_ENABLE_SENSORS_3V3, LOW);

    // put your setup code here, to run once:
    Serial.begin(115200);
    // comment out the below line to cancel the wait for USB connection (needed for native USB)
    //while (!Serial);
    Serial.println("Edge Impulse Inferencing Demo");
	  Wire.begin(); // Start the I2C interface

    //init display
    if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3C for 128x32
#ifdef DEBUG
      Serial.println(F("SSD1306 allocation failed"));
#endif
      for (;;); // Don't proceed, loop forever
    } else {
#ifdef DEBUG
      Serial.println(F("SSD1306 Begun"));
#endif
    }

    display.ssd1306_command(SSD1306_SETCONTRAST);
    display.ssd1306_command(0x00);
    //set pinmodes
    pinMode(VBR1, OUTPUT);
    NRF_P1->PIN_CNF[12] = 0x501; //set high drive

    pinMode(VBR2, OUTPUT);
    //NRF_P1->PIN_CNF[15] = 0x501; //set high drive
    //pinMode(VBR2, OUTPUT);
    //pinMode(VBR3, OUTPUT);
    //pinMode(VBR4, OUTPUT);
    pinMode(LED, OUTPUT);
    pinMode(KEY, OUTPUT);

    // summary of inferencing settings (from model_metadata.h)
    ei_printf("Inferencing settings:\n");
    ei_printf("\tInterval: %.2f ms.\n", (float)EI_CLASSIFIER_INTERVAL_MS);
    ei_printf("\tFrame size: %d\n", EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE);
    ei_printf("\tSample length: %d ms.\n", EI_CLASSIFIER_RAW_SAMPLE_COUNT / 16);
    ei_printf("\tNo. of classes: %d\n", sizeof(ei_classifier_inferencing_categories) /
                                            sizeof(ei_classifier_inferencing_categories[0]));

    run_classifier_init();
    if (microphone_inference_start(EI_CLASSIFIER_SLICE_SIZE) == false) {
        ei_printf("ERR: Could not allocate audio buffer (size %d), this could be due to the window length of your model\r\n", EI_CLASSIFIER_RAW_SAMPLE_COUNT);
        return;
    }
}

/**
 * @brief      Arduino main function. Runs the inferencing loop.
 */
void loop()
{
    if (currentTime % 20000 < 50){
        // reset display
        display.setRotation(1); //rotate 90 degrees
        display.clearDisplay(); //clears display
        display.setTextColor(SSD1306_WHITE); //sets color to white
        display.setTextSize(5.5); //sets text size to 6 (60 pixels)
        display.setCursor(1, 20); //x, y starting coordinates

        print2spaces(myRTC.getHour(h12Flag, pmFlag));
        //display.print(":");
        display.setCursor(1,74); //next line
        print2digits(myRTC.getMinute());
        
        display.display();
    }
    
    //TIME DEPENDENT COMPONENTS ----------------------------------
    currentTime = millis();

    //turn on/off vibrator and led
    if ((currentTime-triggerTime < 400) || ((currentTime-triggerTime > 650) && (currentTime-triggerTime < 1050))) {
        digitalWrite(VBR1, HIGH);
        digitalWrite(VBR2, HIGH);
        //digitalWrite(VBR3, HIGH);
        //digitalWrite(VBR4, HIGH);
        digitalWrite(LED, HIGH);
    } else {
        digitalWrite(VBR1, LOW);
        digitalWrite(VBR2, LOW);
        //digitalWrite(VBR3, LOW);
        //digitalWrite(VBR4, LOW);
        digitalWrite(LED, LOW);
    }

    // keep battery awake code
    if (currentTime % 10000 < 1000){
        digitalWrite(KEY, LOW);
    } else {
        digitalWrite(KEY, HIGH);
    }

    bool m = microphone_inference_record();
    if (!m) {
        ei_printf("ERR: Failed to record audio...\n");
        return;
    }

    signal_t signal;
    signal.total_length = EI_CLASSIFIER_SLICE_SIZE;
    signal.get_data = &microphone_audio_signal_get_data;
    ei_impulse_result_t result = {0};

    EI_IMPULSE_ERROR r = run_classifier_continuous(&signal, &result, debug_nn);
    if (r != EI_IMPULSE_OK) {
        ei_printf("ERR: Failed to run classifier (%d)\n", r);
        return;
    }

    if (++print_results >= 1) { //formerly 1 was (EI_CLASSIFIER_SLICES_PER_MODEL_WINDOW) -- reduces "averaging"` function
        // print the predictions

#ifdef DEBUG_PRED
        ei_printf("Predictions ");
        ei_printf("(DSP: %d ms., Classification: %d ms., Anomaly: %d ms.)",
            result.timing.dsp, result.timing.classification, result.timing.anomaly);
        ei_printf(": \n");
        for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
            ei_printf("    %s: %.5f\n", result.classification[ix].label,
                      result.classification[ix].value);
        }
#endif

    if (currentTime-triggerTime > 1500) {
        //display.print(int(result.classification[NAME_INDEX].value * 100));
        //display.display();
        name_val_total = result.classification[NAME_INDEX].value + result.classification[NAME_PITCH_INDEX].value + result.classification[NAME_AMBIANCE_INDEX].value + result.classification[NAME_AMBIANCE_PITCH_INDEX].value;
        avg = (name_val_total + prev) / 2;

#ifdef DEBUG_AVG
      Serial.print("total name value: ");
      Serial.println(name_val_total);
      //Serial.println();
      Serial.print("avg: ");
      Serial.println(avg);
      Serial.println();
#endif

          if (name_val_total > MASTER_NAME_THRESHOLD){
            triggerTime = millis();
            avg = 0.0;
            prev = 0.0;
            name_val_total = 0.0;
          } else { 
            prev = name_val_total;
          }
    }

#if EI_CLASSIFIER_HAS_ANOMALY == 1
        ei_printf("    anomaly score: %.3f\n", result.anomaly);
#endif

        print_results = 0;
    }
}

/**
 * @brief      PDM buffer full callback
 *             Get data and call audio thread callback
 */
static void pdm_data_ready_inference_callback(void)
{
    int bytesAvailable = PDM.available();

    // read into the sample buffer
    int bytesRead = PDM.read((char *)&sampleBuffer[0], bytesAvailable);

    if (record_ready == true) {
        for (int i = 0; i<bytesRead>> 1; i++) {
            inference.buffers[inference.buf_select][inference.buf_count++] = sampleBuffer[i];

            if (inference.buf_count >= inference.n_samples) {
                inference.buf_select ^= 1;
                inference.buf_count = 0;
                inference.buf_ready = 1;
            }
        }
    }
}

/**
 * @brief      Init inferencing struct and setup/start PDM
 *
 * @param[in]  n_samples  The n samples
 *
 * @return     { description_of_the_return_value }
 */
static bool microphone_inference_start(uint32_t n_samples)
{
    inference.buffers[0] = (signed short *)malloc(n_samples * sizeof(signed short));

    if (inference.buffers[0] == NULL) {
        return false;
    }

    inference.buffers[1] = (signed short *)malloc(n_samples * sizeof(signed short));

    if (inference.buffers[1] == NULL) {
        free(inference.buffers[0]);
        return false;
    }

    sampleBuffer = (signed short *)malloc((n_samples >> 1) * sizeof(signed short));

    if (sampleBuffer == NULL) {
        free(inference.buffers[0]);
        free(inference.buffers[1]);
        return false;
    }

    inference.buf_select = 0;
    inference.buf_count = 0;
    inference.n_samples = n_samples;
    inference.buf_ready = 0;

    // configure the data receive callback
    PDM.onReceive(&pdm_data_ready_inference_callback);

    PDM.setBufferSize((n_samples >> 1) * sizeof(int16_t));

    // initialize PDM with:
    // - one channel (mono mode)
    // - a 16 kHz sample rate
    if (!PDM.begin(1, EI_CLASSIFIER_FREQUENCY)) {
        ei_printf("Failed to start PDM!");
    }

    // set the gain, defaults to 20
    PDM.setGain(135);

    record_ready = true;

    return true;
}

/**
 * @brief      Wait on new data
 *
 * @return     True when finished
 */
static bool microphone_inference_record(void)
{
    bool ret = true;

    if (inference.buf_ready == 1) {
        ei_printf(
            "Error sample buffer overrun. Decrease the number of slices per model window "
            "(EI_CLASSIFIER_SLICES_PER_MODEL_WINDOW)\n");
        ret = false;
    }

    while (inference.buf_ready == 0) {
        delay(1);
    }

    inference.buf_ready = 0;

    return ret;
}

/**
 * Get raw audio signal data
 */
static int microphone_audio_signal_get_data(size_t offset, size_t length, float *out_ptr)
{
    numpy::int16_to_float(&inference.buffers[inference.buf_select ^ 1][offset], out_ptr, length);

    return 0;
}

/**
 * @brief      Stop PDM and release buffers
 */
static void microphone_inference_end(void)
{
    PDM.end();
    free(inference.buffers[0]);
    free(inference.buffers[1]);
    free(sampleBuffer);
}

/*
#if !defined(EI_CLASSIFIER_SENSOR) || EI_CLASSIFIER_SENSOR != EI_CLASSIFIER_SENSOR_MICROPHONE
#error "Invalid model for current sensor."
#endif*/

void print2digits(int number) {
  if (number < 10){
    display.print("O");
    if (number == 0){
      display.print("O");
    } else{
      display.print(number);
    }
  } else {
    display.print(number/10);
    if (number % 10 == 0) {
      display.print("O");
    } else {
      display.print(number%10);
    }
  }
}

void print2spaces(int number) {
  if (number < 10){
    display.print(" ");
    display.print(number);
  } else {
    display.print(number/10);
    if (number % 10 == 0) {
      display.print("O");
    } else {
      display.print(number%10);
    }
  }
}

void classify(ei_impulse_result_classification_t values){
  prev_max = 0;
  max = 0;
  prev_index = 0;
  index = 0;

  for (size_t ix = 0; ix < EI_CLASSIFIER_LABEL_COUNT; ix++) {
    if (result.classification[ix].value > max){
      prev_max = max
      max = result.classification[ix].value;
      prev_index = index;
      index = ix;
    }

    if (index >= 3 && index <= 6){ //if max = "name"
      if (prev_index <= 2 || prev_index == 7){ //if max = name AND second max = "not name"
        if (max - prev_max > 0.1){ //if diff > 0.1
          return "name"
        } else {
          return "not name"
        }
      } else { //if max and second max = "name"
        return "name"
      }
    } else { //if max = "not"
      return "not name"
    }
  } 
}
