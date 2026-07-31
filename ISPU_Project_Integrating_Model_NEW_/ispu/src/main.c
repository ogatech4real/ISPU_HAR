/**
  ******************************************************************************
  * @file    main.c
  * @brief   ISPU-HAR native ISPU application.
  *
  * Input order:
  *   [acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z]
  *
  * Class mapping:
  *   0 = brushing
  *   1 = chopping
  *   2 = cleaning
  *   3 = idle
  *   4 = pick_drop
  ******************************************************************************
  */

#include "peripherals.h"
#include "reg_map.h"

#include <stdint.h>
#include <stdbool.h>

#include "stai.h"
#include "network.h"
#include "network_utils.h"

/* Model geometry */
#define HAR_WINDOW_SIZE          (120u)
#define HAR_CHANNEL_COUNT        (6u)
#define HAR_CLASS_COUNT          (5u)

/*
 * ISM330IS sensitivities selected in conf.txt:
 * accelerometer: +/-8 g       -> 0.244 mg/LSB = 0.000244 g/LSB
 * gyroscope:     +/-2000 dps  -> 70 mdps/LSB = 0.070 dps/LSB
 */
#define ACC_SENS_G_PER_LSB       (0.000244f)
#define GYR_SENS_DPS_PER_LSB     (0.070000f)

/* Quantisation parameters from network_details.h */
#define INPUT_SCALE              (0.005275879520922899f)
#define INPUT_ZERO_POINT         (-21)

/* Training-set normalisation parameters */
static const float feature_mean[HAR_CHANNEL_COUNT] = {
    -0.06845613f,
     0.28765209f,
     0.53943266f,
     1.65998318f,
    -3.73946091f,
    -0.92286052f
};

static const float feature_std[HAR_CHANNEL_COUNT] = {
     0.52400529f,
     0.55673910f,
     0.56340278f,
    38.53294971f,
    44.11240981f,
    61.02969762f
};

void __attribute__((signal)) algo_00_init(void);
void __attribute__((signal)) algo_00(void);

static __attribute__((aligned(8)))
stai_network net[STAI_NETWORK_CONTEXT_SIZE];

static stai_ptr input_buffers[STAI_NETWORK_IN_NUM];
static stai_ptr output_buffers[STAI_NETWORK_OUT_NUM];

static volatile uint32_t int_status;
static uint16_t sample_index;

/* Convert a floating-point normalised feature to signed INT8. */
static int8_t quantize_input(float value)
{
    const float scaled = (value / INPUT_SCALE) + (float)INPUT_ZERO_POINT;
    int32_t quantized;

    if (scaled >= 0.0f) {
        quantized = (int32_t)(scaled + 0.5f);
    } else {
        quantized = (int32_t)(scaled - 0.5f);
    }

    if (quantized > 127) {
        quantized = 127;
    } else if (quantized < -128) {
        quantized = -128;
    }

    return (int8_t)quantized;
}

/* Convert one raw six-axis sample to the model's quantised input format. */
static void store_sample(int8_t *input, uint16_t index)
{
    float sample[HAR_CHANNEL_COUNT];

    sample[0] = (float)cast_sint16_t(ISPU_ARAW_X) * ACC_SENS_G_PER_LSB;
    sample[1] = (float)cast_sint16_t(ISPU_ARAW_Y) * ACC_SENS_G_PER_LSB;
    sample[2] = (float)cast_sint16_t(ISPU_ARAW_Z) * ACC_SENS_G_PER_LSB;

    sample[3] = (float)cast_sint16_t(ISPU_GRAW_X) * GYR_SENS_DPS_PER_LSB;
    sample[4] = (float)cast_sint16_t(ISPU_GRAW_Y) * GYR_SENS_DPS_PER_LSB;
    sample[5] = (float)cast_sint16_t(ISPU_GRAW_Z) * GYR_SENS_DPS_PER_LSB;

    const uint16_t base = (uint16_t)(index * HAR_CHANNEL_COUNT);

    for (uint8_t channel = 0u; channel < HAR_CHANNEL_COUNT; ++channel) {
        const float normalized =
            (sample[channel] - feature_mean[channel]) / feature_std[channel];

        input[base + channel] = quantize_input(normalized);
    }
}

/* Return the index of the largest signed INT8 output score. */
static uint8_t output_argmax(const int8_t *output)
{
    uint8_t best_class = 0u;
    int8_t best_score = output[0];

    for (uint8_t class_index = 1u;
         class_index < HAR_CLASS_COUNT;
         ++class_index) {
        if (output[class_index] > best_score) {
            best_score = output[class_index];
            best_class = class_index;
        }
    }

    return best_class;
}

/* Publish class ID and raw output scores through ISPU output registers. */
static void publish_result(uint8_t predicted_class, const int8_t *output)
{
    cast_uint8_t(ISPU_DOUT_00) = predicted_class;
    cast_sint8_t(ISPU_DOUT_01) = output[predicted_class];

    cast_sint8_t(ISPU_DOUT_02) = output[0];
    cast_sint8_t(ISPU_DOUT_03) = output[1];
    cast_sint8_t(ISPU_DOUT_04) = output[2];
    cast_sint8_t(ISPU_DOUT_05) = output[3];
    cast_sint8_t(ISPU_DOUT_06) = output[4];

    /*
     * DOUT_07 status:
     *   0 = valid inference result
     *   1 = inference/runtime error
     */
    cast_uint8_t(ISPU_DOUT_07) = 0u;
}

void __attribute__((signal)) algo_00_init(void)
{
    (void)stai_runtime_init();
    (void)stai_network_init(net);

    init_network_buffers(net, input_buffers, output_buffers);

    sample_index = 0u;

    cast_uint8_t(ISPU_DOUT_00) = 0xFFu; /* no prediction yet */
    cast_uint8_t(ISPU_DOUT_07) = 0u;
}

void __attribute__((signal)) algo_00(void)
{
    int8_t *const input = (int8_t *)input_buffers[0];

    /*
     * algo_00() runs at the configured common accelerometer/gyroscope ODR.
     * One channel-last sample occupies six consecutive bytes.
     */
    store_sample(input, sample_index);
    ++sample_index;

    if (sample_index < HAR_WINDOW_SIZE) {
        return;
    }

    /*
     * The network input window is now complete:
     * [1, 120, 6], signed INT8, channel-last.
     */
    const stai_return_code result =
        stai_network_run(net, STAI_MODE_SYNC);

    if (result >= STAI_ERROR_GENERIC) {
        cast_uint8_t(ISPU_DOUT_07) = 1u;
        sample_index = 0u;
        int_status |= 0x1u;
        return;
    }

    const int8_t *const output = (const int8_t *)output_buffers[0];
    const uint8_t predicted_class = output_argmax(output);

    publish_result(predicted_class, output);

    /*
     * Start a new non-overlapping 120-sample window.
     * This avoids allocating an additional overlap buffer in the limited
     * 8 KiB ISPU data RAM.
     */
    sample_index = 0u;

    /* Signal that a new HAR result is available. */
    int_status |= 0x1u;
}

int main(void)
{
    /* Set boot-done flag. */
    uint8_t status = cast_uint8_t(ISPU_STATUS);
    status |= 0x04u;
    cast_uint8_t(ISPU_STATUS) = status;

    /* Enable algorithm interrupt-request generation. */
    cast_uint8_t(ISPU_GLB_CALL_EN) = 0x01u;

    while (true) {
        stop_and_wait_start_pulse;

        /* Reset status registers and interrupts. */
        int_status = 0u;
        cast_uint32_t(ISPU_INT_STATUS) = 0u;
        cast_uint8_t(ISPU_INT_PIN) = 0u;

        /* Run all algorithms enabled for this time slot. */
        cast_uint32_t(ISPU_CALL_EN) =
            cast_uint32_t(ISPU_ALGO) << 1;

        while (cast_uint32_t(ISPU_CALL_EN) != 0u) {
        }

        /* Resolve interrupt routing. */
        uint8_t int_pin = 0u;
        int_pin |=
            ((int_status & cast_uint32_t(ISPU_INT1_CTRL)) > 0u)
                ? 0x01u
                : 0x00u;
        int_pin |=
            ((int_status & cast_uint32_t(ISPU_INT2_CTRL)) > 0u)
                ? 0x02u
                : 0x00u;

        cast_uint32_t(ISPU_INT_STATUS) = int_status;
        cast_uint8_t(ISPU_INT_PIN) = int_pin;
    }
}
