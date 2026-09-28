# Job Posting Screenshot Checker

Reads screenshots of job postings from a folder, extracts the text with OCR, and estimates whether each posting looks legitimate or like a scam.

## How it works

The tool uses a two-stage pipeline to analyze job posting screenshots:

### Stage 1: Content Classification
Determines if the image contains an actual job posting using:
- Keyword detection (checks for hiring-related terms)
- `laya` Router classification to identify document type (job posting, resume, or other)
- Requires at least 4 matching keywords OR model confirmation to proceed

### Stage 2: Scam Analysis (for confirmed job postings)
1. **OCR** – [EasyOCR](https://github.com/JaidedAI/EasyOCR) extracts text from the image
2. **Classification** – the `laya` Router analyzes the text for red flags including:
   - Overall verdict (legitimate, suspicious, likely scam)
   - Scam score (0-1 probability scale)
   - Specific flags: upfront payment requests, unrealistic pay, off-platform contact, vague details, urgency pressure
3. **Code-level checks** – email domains are validated:
   - Company domains lower the off-platform-contact flag
   - Free mail domains (gmail, yahoo, outlook, etc.) raise it
4. **Decision** – combines all signals into one of three outcomes:
   - **Likely fake** – hard flag (upfront payment or off-platform contact) above 70%, or verdict is `likely_scam`
   - **Suspicious** – two or more soft flags above 60%, or verdict is `suspicious`
   - **Looks legitimate** – no significant red flags detected

## Project structure

```text
├── main.py             # main script
├── config.py           # loads .env and resolves paths
├── .env                # your local settings (not committed)
├── .env.example        # template for .env
├── requirements.txt
└── job_images/         # put screenshots here
```

> Never name a script `laya.py`. It shadows the installed library and causes a circular import error.

## Setup

Requires Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`requirements.txt`:

```text
laya
easyocr
torch
torchvision
python-dotenv
```

### Optional: GPU (NVIDIA only)

Check for a GPU with `nvidia-smi`, then install the CUDA build of PyTorch (pick the command matching your CUDA version at [pytorch.org](https://pytorch.org/get-started/locally)):

```powershell
python -m pip uninstall -y torch torchvision
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
python -c "import torch; print(torch.cuda.is_available())"
```

Then make the OCR reader use it automatically:

```python
import torch
_reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
```

Without a GPU everything still works on the CPU, just more slowly.

## Configuration

Copy `.env.example` to `.env`:

```text
IMAGE_FOLDER=job_images
# HF_TOKEN=hf_your_token_here
```

| Variable | Description | Default |
|---|---|---|
| `IMAGE_FOLDER` | Folder containing screenshots. Relative paths are resolved from the folder that contains `config.py`, not from your terminal's current directory. Absolute paths also work (use forward slashes on Windows). | `job_images` |
| `HF_TOKEN` | Optional Hugging Face token. Removes the "unauthenticated requests" warning. | none |

Add `.env` to `.gitignore`.

## Usage

Analyze every image in the configured folder:

```powershell
python .\main.py
```

Override the folder, or analyze a single file:

```powershell
python .\main.py "C:\path\to\folder"
python .\main.py "C:\path\to\screenshot.png"
```

Supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`.

For each image the script prints the extracted text, the verdict, the raw scam score, the email domains found, each red-flag probability, and the final decision.

## First run

The first run downloads the `laya` checkpoint from Hugging Face (about 115 MB) and the EasyOCR models. Both are cached, so later runs start quickly.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ImportError: cannot import name 'Router'` | A local file is named `laya.py`. Rename it and delete `__pycache__`. |
| `ModuleNotFoundError: easyocr` | Run `python -m pip install -r requirements.txt` inside the active `.venv`. |
| `Folder not found` / `No images found` | Check `IMAGE_FOLDER` in `.env` and that the folder contains supported images. |
| `Using CPU` message | Harmless. See the GPU section to switch. |
| Symlink warning from `huggingface_hub` | Harmless. Set `HF_HUB_DISABLE_SYMLINKS_WARNING=1` or enable Windows Developer Mode. |
| `RuntimeWarning` about invalid temperatures | Checkpoint packaging quirk. Probabilities are useful for ranking and thresholds, not exact percentages. |
| Wrong results on a clean posting | Check the printed OCR text. Blurry screenshots drop characters, including in email addresses. |

## Limitations

- The model judges **wording only**. It cannot verify that a company, recruiter, or domain actually exists.
- Short, terse postings can look "vague" to the model even when they are real.
- Thresholds (0.6 / 0.7) are starting points. Tune them against a set of postings you have labeled yourself.
- Treat "Looks legitimate" as "no red flags found", not as a guarantee. Always verify the company independently before sharing personal information or documents.