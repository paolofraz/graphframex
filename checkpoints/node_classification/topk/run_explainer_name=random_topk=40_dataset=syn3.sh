#!/bin/bash

#SBATCH --time=600
#SBATCH --gpus-per-task=2
#SBATCH --mem=5000
#SBATCH --output=/cluster/home/kamara/Explain/checkpoints/topk/logs/_explainer_name=random_topk=40_dataset=syn3.stdout
#SBATCH --error=/cluster/home/kamara/Explain/checkpoints/topk/logs/_explainer_name=random_topk=40_dataset=syn3.stderr
#SBATCH --job-name=topk_explainer_name=random_topk=40_dataset=syn3
#SBATCH --open-mode=append
#SBATCH --signal=B:USR1@120

cd .
EXP_NUMBER=$SLURM_ARRAY_TASK_ID
export JOBNAME="topk_explainer_name=random_topk=40_dataset=syn3"
LOG_STDOUT="/cluster/home/kamara/Explain/checkpoints/topk/logs/_explainer_name=random_topk=40_dataset=syn3.stdout"
LOG_STDERR="/cluster/home/kamara/Explain/checkpoints/topk/logs/_explainer_name=random_topk=40_dataset=syn3.stderr"

trap_handler () {
   echo "Caught signal" >> $LOG_STDOUT
   sbatch --begin=now+120 /cluster/home/kamara/Explain/checkpoints/topk/run_explainer_name=random_topk=40_dataset=syn3.sh
   exit 0
}
function ignore {
   echo "Ignored SIGTERM" >> $LOG_STDOUT
}

trap ignore TERM
trap trap_handler USR1
echo "Git hash:" >> $LOG_STDOUT
echo $(git rev-parse HEAD 2> /dev/null) >> $LOG_STDOUT

which python >> $LOG_STDOUT
echo "---Beginning program ---" >> $LOG_STDOUT
PYTHONUNBUFFERED=yes MKL_THREADING_LAYER=GNU python exp_synthetic/main.py \
--explainer_name random --topk 40 --dataset syn3 --num_test_nodes 100 --data_save_dir data --gpu True --dest /cluster/home/kamara/Explain/checkpoints/topk/_explainer_name=random_topk=40_dataset=syn3 >> $LOG_STDOUT 2>> $LOG_STDERR && echo 'JOB_FINISHED' >> $LOG_STDOUT &
wait $!