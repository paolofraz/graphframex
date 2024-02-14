# Define the path to the data, model, logs, results, and colors
#
from pathlib import Path

# Define the path to the data, model, logs, results, and colors
# Get this file path
CKPT_ROOT = Path(__file__).resolve().parents[3]
#CKPT_ROOT = Path("../../../").resolve()
if CKPT_ROOT.exists():
	DATA_DIR = CKPT_ROOT / "Datasets/"
	MODEL_DIR = CKPT_ROOT / "Models/"
	LOG_DIR = CKPT_ROOT / "Logs/"
	RESULT_DIR = CKPT_ROOT / "Results/"
	MASK_DIR = CKPT_ROOT / "Mask/"
	FIGURE_DIR = CKPT_ROOT / "Figures/"

	# Create the folders if they don't exist
	DATA_DIR.mkdir(exist_ok=True)
	MODEL_DIR.mkdir(exist_ok=True)
	LOG_DIR.mkdir(exist_ok=True)
	RESULT_DIR.mkdir(exist_ok=True)
	MASK_DIR.mkdir(exist_ok=True)
	FIGURE_DIR.mkdir(exist_ok=True)

