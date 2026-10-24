"""The browser reports configured routes separately from completed responses."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_route_display_does_not_claim_a_backup_was_used():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js required to execute browser helpers')
    script = """
const {modelRouteDescription,completedModels}=require(process.argv[1]);
const config={models:{producer:'openai/gpt-4.1-mini',critic:'google/gemini-2.5-flash'},model_routes:{producer:{models:['openai/gpt-4.1-mini','mistralai/mistral-medium-3.1']}}};
console.log(JSON.stringify({description:modelRouteDescription(config),none:completedModels({}),actual:completedModels({calls:[{requested_model:'openai/gpt-4.1-mini',returned_model:'mistralai/mistral-medium-3.1'},{returned_model:'mistralai/mistral-medium-3.1'}]}),legacy:completedModels({calls:[{model:'google/gemini-2.5-flash'}]})}));
"""
    result = subprocess.run([node, '-e', script, str(ROOT / 'web/app.js')], check=True, capture_output=True, text=True, timeout=10)
    value = json.loads(result.stdout)
    assert 'openai/gpt-4.1-mini produces; backup: mistralai/mistral-medium-3.1' in value['description']
    assert 'google/gemini-2.5-flash reviews independently' in value['description']
    assert value['none'] == []
    assert value['actual'] == ['mistralai/mistral-medium-3.1']
    assert value['legacy'] == ['google/gemini-2.5-flash']
