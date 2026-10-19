import json
from pathlib import Path


def test_templates_have_unique_ids_and_prompt_fields():
    template_path = Path(__file__).resolve().parents[1] / "app" / "templates.json"
    templates = json.loads(template_path.read_text(encoding="utf-8"))
    assert len(templates) >= 1
    ids = [str(template["id"]) for template in templates]
    assert len(ids) == len(set(ids))
    for template in templates:
        assert template.get("name")
        assert isinstance(template.get("fields"), list)
        assert template.get("ai_prompt")
        field_ids = [field["id"] for field in template["fields"]]
        assert len(field_ids) == len(set(field_ids))
        for field_id in field_ids:
            assert "{" + field_id + "}" in template["ai_prompt"], (template["id"], field_id)
