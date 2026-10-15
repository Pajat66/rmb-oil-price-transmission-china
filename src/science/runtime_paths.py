"""R3 science requires an explicitly supplied isolated work directory."""
from pathlib import Path
import os
value=os.environ.get('RMB_R3_WORKDIR')
if not value:
    raise RuntimeError('Set RMB_R3_WORKDIR to an isolated scientific workspace in authorized R3. Licensed monthly inputs are not bundled.')
SCIENTIFIC_WORK_DIR=Path(value).expanduser().resolve()
