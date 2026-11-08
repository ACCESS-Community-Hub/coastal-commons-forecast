#!/bin/bash

module load pbs
module load use.own
module use /g/data/vk83/modules
module load cc-forecast/2026.11.0

python3 $TASK_SCRIPT_FILE --config-path $TASK_CONFIG_DIR --config-name $TASK_CONFIG_FILE
