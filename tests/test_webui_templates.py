from app.webui.templates.desk import _DESK_HTML
from app.webui.templates.environment import _ENV_HTML
from app.webui.templates.images import _IMAGES_HTML
from app.webui.templates.settings import _SETTINGS_HTML


def test_authenticated_pages_share_editorial_shell():
    pages = {
        "desk": _DESK_HTML,
        "environment": _ENV_HTML,
        "images": _IMAGES_HTML,
        "settings": _SETTINGS_HTML,
    }

    for page_id, html in pages.items():
        assert f'<body data-page="{page_id}">' in html
        assert '<header class="topbar">' in html
        assert 'class="page-title"' in html
        assert 'class="page-desc"' in html
        assert '.page-title{margin:0 0 1.35rem;padding-bottom:1rem;border-bottom:1px solid var(--line);font-size:clamp(2rem,6vw,4rem);line-height:.92;letter-spacing:-.06em;font-weight:700}' in html
        assert 'class="theme-toggle"' in html
        assert 'class="site-footer"' in html


def test_pages_use_shared_visual_primitives_for_feedback_and_controls():
    assert 'class="metric-grid"' in _DESK_HTML
    assert 'class="metric-grid"' in _ENV_HTML
    assert 'class="card control-card"' in _ENV_HTML
    assert 'class="loading-state"' in _DESK_HTML
    assert 'class="loading-state"' in _ENV_HTML
    assert 'class="tog-row"' in _IMAGES_HTML
    assert 'class="tog-row"' in _SETTINGS_HTML
    assert 'class="status-badge"' in _SETTINGS_HTML
    assert 'class="acc-head" aria-expanded="true"' in _SETTINGS_HTML
    assert 'aria-controls="acc-body-weather"' in _SETTINGS_HTML
    assert "setAttribute('aria-expanded','false')" in _SETTINGS_HTML


def test_presence_settings_expose_debounce_durations():
    assert 'id="p-unoccupied-after"' in _SETTINGS_HTML
    assert 'id="p-occupied-after"' in _SETTINGS_HTML
    assert 'sl.unoccupied_after_seconds??180' in _SETTINGS_HTML
    assert 'sl.occupied_after_seconds??30' in _SETTINGS_HTML
    assert 'unoccupied_after_seconds:+document.getElementById' in _SETTINGS_HTML
    assert 'occupied_after_seconds:+document.getElementById' in _SETTINGS_HTML
    assert '持續暗光多久算離開' in _SETTINGS_HTML
    assert '持續亮光多久恢復在席' in _SETTINGS_HTML
    assert '<span>0 亮</span><span>1023 暗</span>' in _SETTINGS_HTML


def test_image_workflow_uses_class_based_view_switching():
    assert 'id="view-crop" class="is-hidden"' in _IMAGES_HTML
    assert 'id="view-preview" class="is-hidden"' in _IMAGES_HTML
    assert "classList.toggle('is-hidden', v !== name)" in _IMAGES_HTML
    assert 'role="dialog" aria-modal="true"' in _IMAGES_HTML
    assert 'role="button"' in _IMAGES_HTML


def test_environment_charts_have_accessible_names():
    assert 'role="img" aria-label="\'+chartLabel+\'，此時段無資料"' in _ENV_HTML
    assert 'role="img" aria-label="\'+chartLabel+\'趨勢圖"' in _ENV_HTML
