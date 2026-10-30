import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import ui.explanations as page
from test_explanations import energy_record

APP=Path(__file__).resolve().parents[1]/'app.py'


class ExplanationPageTests(unittest.TestCase):
    def test_history_write_failure_does_not_display_an_unsaved_answer(self):
        self.open(energy_record())
        with patch.object(page,'submit_explanation',side_effect=PermissionError('test storage failure')):
            self.app.button(key='request-explanation').click().run()
        self.assertEqual(list(self.app.exception),[])
        self.assertNotIn('explanation_result',self.app.session_state)
        self.assertFalse(self.history.exists())
        self.assertIn('could not be saved',' '.join(e.value for e in self.app.error))

    def setUp(self):
        temporary=TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.history=self.root/'explanations.jsonl'
        for obj,field,value in ((page,'RUNTIME_DIRECTORY',self.root),(page,'HISTORY_PATH',self.history)):
            p=patch.object(obj,field,value);p.start();self.addCleanup(p.stop)
        p=patch.dict('os.environ',{'ELEC5620_API_KEY':''});p.start();self.addCleanup(p.stop)
        self.app=AppTest.from_file(str(APP),default_timeout=120)

    def open(self,record=None):
        if record is not None:
            (self.root/'energy_comfort.jsonl').write_text(json.dumps(record)+'\n',encoding='utf-8')
        self.app.run()
        self.app.sidebar.radio[0].set_value('Decision explanations').run()
        self.assertEqual(list(self.app.exception),[])

    def test_empty_history_is_clear_without_crashing(self):
        self.open()
        self.assertIn('No stored decisions yet',' '.join(i.value for i in self.app.info))

    def test_request_saved_history_restored_and_simpler_request_is_separate(self):
        self.open(energy_record())
        self.app.button(key='request-explanation').click().run()
        self.assertEqual(list(self.app.exception),[])
        first=self.app.session_state['explanation_result']
        self.assertEqual(first['evidence_status'],'CONSISTENT')
        self.assertEqual(first['review_status'],'NOT_REQUIRED')
        self.assertTrue(self.history.exists())
        self.app.selectbox(key='explanation_style').set_value('Simpler').run()
        self.app.button(key='request-explanation').click().run()
        second=self.app.session_state['explanation_result']
        self.assertEqual(second['request']['source_sha256'],first['request']['source_sha256'])
        self.assertNotEqual(second['request']['request_id'],first['request']['request_id'])
        self.assertLess(len(second['facts']),len(first['facts']))
        # Fresh app session loads the persisted answers, not old Session State.
        self.app=AppTest.from_file(str(APP),default_timeout=120)
        self.open()
        self.assertEqual(len([e for e in self.app.expander if 'Why was this decision made?' in e.label]),2)

    def test_failed_or_sensitive_explanation_waits_for_operator_review(self):
        self.open(energy_record(offline=True))
        self.app.button(key='request-explanation').click().run()
        self.assertEqual(self.app.session_state['explanation_result']['review_status'],'PENDING')
        self.assertFalse(any(b.label=='Approve factual explanation' for b in self.app.button))
        self.app.checkbox(key='explanation_operator').set_value(True).run()
        self.app.button(key='explanation-review-True').click().run()
        self.assertEqual(list(self.app.exception),[])
        self.assertEqual(self.app.session_state['explanation_result']['review_status'],'APPROVED')
        self.assertEqual(json.loads(self.history.read_text(encoding='utf-8').splitlines()[-1])['record_type'],'explanation_review')

    def test_unconfigured_ai_falls_back_and_history_corruption_is_ignored(self):
        self.open(energy_record())
        self.history.write_text('bad json\nnull\n',encoding='utf-8')
        self.app.toggle(key='explanation_use_ai').set_value(True).run()
        self.app.button(key='request-explanation').click().run()
        self.assertEqual(list(self.app.exception),[])
        self.assertIn('FALLBACK',self.app.session_state['explanation_result']['ai_status'])
