from app.crochet_engine.model_sheet import render_model_sheet


def test_model_sheet_is_data_url_and_contains_parts():
    design = {
        'subject': 'Orsetto Teddy',
        'parts': [
            {'id':'body','label':'Corpo','role':'body','count':1},
            {'id':'arm','label':'Braccio','role':'arm','count':2,'symmetry_group':'arms'},
            {'id':'ear','label':'Orecchio','role':'ear','count':2,'symmetry_group':'ears'},
        ],
    }
    out = render_model_sheet(design)
    assert out.startswith('data:image/svg+xml;base64,')
    import base64
    svg = base64.b64decode(out.split(',',1)[1]).decode('utf-8')
    assert 'MODEL SHEET' in svg
    assert 'Orsetto Teddy' in svg
    assert 'Braccio' in svg
    assert '×2' in svg
    assert 'arms' in svg
