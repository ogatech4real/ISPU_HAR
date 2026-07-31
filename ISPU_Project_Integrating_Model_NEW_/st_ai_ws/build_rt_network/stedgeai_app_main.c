/**
 ******************************************************************************
 * @file    stedgeai_app_main.c
 * @author  MCD/AIS Team
 * @brief   Minimal main template to use the ST AI generated c-model using the
            STAI api.
 ******************************************************************************
 * @attention
 *
 * <h2><center>&copy; Copyright (c) 2024 STMicroelectronics.
 * All rights reserved.</center></h2>
 *
 * This software is licensed under terms that can be found in the LICENSE file in
 * the root directory of this software component.
 * If no LICENSE file comes with this software, it is provided AS-IS.
 *
 ******************************************************************************
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "network.h"
#include "network_data.h"

/* Global handle to reference the instantiated C-model */
STAI_NETWORK_CONTEXT_DECLARE(m_network, STAI_NETWORK_CONTEXT_SIZE)

/* Array to store the data of the activation buffers */
STAI_ALIGNED(STAI_NETWORK_ACTIVATION_1_ALIGNMENT)
static uint8_t activations_1[STAI_NETWORK_ACTIVATION_1_SIZE_BYTES];


/* Array to store the data of the input tensors */
/* -> data_in_1 is allocated in activations buffer */

/* Array to store the data of the output tensors */
/* -> data_out_1 is allocated in activations buffer */

static stai_ptr m_inputs[STAI_NETWORK_IN_NUM];
static stai_ptr m_outputs[STAI_NETWORK_OUT_NUM];
static stai_ptr m_acts[STAI_NETWORK_ACTIVATIONS_NUM];

int aiInit(void);
stai_return_code aiRun(void);
void main_loop(void);
int main(void);

/* 
 * Bootstrap
 */
int aiInit(void)
{
  stai_size _dummy;

  /* -- Create and initialize the c-model */

  /* Initialize the instance */
  stai_network_init(m_network);


  /* -- Set the @ of the activation buffers */

  /* Activation buffers are allocated in the user/app space */
  m_acts[0] = (stai_ptr)activations_1;
  stai_network_set_activations(m_network, m_acts, STAI_NETWORK_ACTIVATIONS_NUM);
  stai_network_get_activations(m_network, m_acts, &_dummy);



  /* -- Set the @ of the input/output buffers */

  /* Input buffers are allocated in the activations buffer */
  stai_network_get_inputs(m_network, m_inputs, &_dummy);

  /* Output buffers are allocated in the activations buffer */
  stai_network_get_outputs(m_network, m_outputs, &_dummy);

  return 0;
}

/* 
 * Run inference
 */
stai_return_code aiRun()
{
  stai_return_code res;

  res = stai_network_run(m_network, STAI_MODE_SYNC);
  
  return res;
}

/* 
 * Example of main loop function
 */
void main_loop()
{

  aiInit();

  
  while (1) {
    /* 1 - Acquire, pre-process and fill the input buffers */
    // acquire_and_process_data(...);

    /* 2 - Call inference engine */
    aiRun();

    /* 3 - Post-process the predictions */
    // post_process(...);
  }
}

/* 
 * Example of system initialization function
 */
void SystemInit(void)
{

}

/* 
 * Example of main application function
 */
int main()
{
  SystemInit();
  main_loop();
  return 0;
}
