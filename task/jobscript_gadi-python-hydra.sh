#!/bin/bash

module load pbs
module load use.own
module use /g/data/yj27/public/modules
module load pyvenv/seacofs-ops

python3 $TASK_SCRIPT_FILE --config-path $TASK_CONFIG_DIR --config-name $TASK_CONFIG_FILE
