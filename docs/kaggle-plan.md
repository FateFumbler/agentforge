# Kaggle plan for AgentForge

## Resources we have to design around
Grounded from Kaggle docs and hackathon rules:

### Hackathon submission requirements
A valid submission needs:
- Kaggle writeup
- public video
- public code repository
- live demo
- media gallery

### Kaggle notebook environment
- 12 hour max execution time for CPU and GPU notebook sessions
- 20 GB auto-saved disk in `/kaggle/working`
- 4 CPU cores
- 29 GB RAM on T4 x2 GPU sessions
- 2 x NVIDIA Tesla T4 GPUs in T4 x2 sessions
- weekly GPU quota of 30 hours or sometimes higher depending on demand/resources

### Competition rules that matter for us
- one submission per team
- max team size 5
- external data and tools are allowed if publicly accessible or reasonably accessible at minimal cost
- final winning solution must be reproducible from code and docs
- public code repo is mandatory

## What to use Kaggle for
Kaggle is best used here for:
- public reproducible notebook demo
- Gemma model usage in a familiar public environment
- lightweight inference and evaluation
- public-facing proof that the workflow is real

Kaggle is not the place for:
- long-running product hosting
- heavy model training as the core dependency
- fragile multi-service backend orchestration

## Recommended technical shape
### Local repo
Keep the source of truth in GitHub.

### Kaggle notebook
Create one primary notebook that:
1. clones or pulls the public repo
2. installs lightweight dependencies
3. attaches a Gemma model from Kaggle Models, if available to the account
4. runs scanner on sample workspace
5. generates a manifest draft
6. validates and previews manifest
7. exports package artifact into `/kaggle/working`

### Demo artifact
The notebook should produce:
- manifest.json
- preview summary
- exported zip or portable folder
- before/after screenshots for the writeup/video

## How to use this on Kaggle
### Notebook setup
1. Open Kaggle and join the Gemma 4 Good Hackathon.
2. Create a new notebook.
3. In Settings:
   - enable Internet while iterating
   - set Accelerator to T4 x2 GPU if available
4. Add required inputs:
   - Gemma 4 model from Kaggle Models, if accessible
   - optional sample workspace dataset or notebook output if we package example data separately
5. Clone the repo in a cell:
```bash
!git clone https://github.com/FateFumbler/agentforge.git
%cd agentforge
```
6. Install dependencies:
```bash
!python3 -m pip install -U pip
!pip install -r requirements.txt
```
7. Run the demo pipeline:
```bash
!python3 -m agentforge.cli scan --input examples/openclaw-sample --output artifacts/scan.json
!python3 -m agentforge.cli generate-manifest --scan artifacts/scan.json --output artifacts/manifest.json
!python3 -m agentforge.cli preview --manifest artifacts/manifest.json --output artifacts/preview.json
!python3 -m agentforge.cli package --manifest artifacts/manifest.json --input examples/openclaw-sample --output /kaggle/working/agentforge-package.zip
```

## GPU usage strategy
Use GPUs only for actual Gemma inference or any small benchmark/demo run.
Do not leave GPU sessions idle.
Do not burn quota on packaging, schema validation, or filesystem scanning.
Use CPU for scanner, schema validation, packaging, and import tests.

## Overnight execution strategy
### On local machine
- implement product and tests
- keep repo as source of truth
- prepare demo sample workspace

### On Kaggle
- validate notebook reproducibility
- validate Gemma-backed manifest generation
- capture outputs for writeup and video

## Suggested messaging for the submission
AgentForge makes AI agents portable, inspectable, and easier to share. Gemma 4 is the reasoning layer that converts messy real-world agent workspaces into structured manifests that can be previewed, exported, and imported with minimal manual setup.

## Immediate build tasks
1. schema and CLI contract
2. workspace scanner
3. Gemma prompt and generator
4. package and import flows
5. Kaggle notebook
6. writeup and demo assets