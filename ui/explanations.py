"""Resident explanation requests over stored domain evidence, plus history."""
import json
import os
from pathlib import Path
from uuid import uuid4

import streamlit as st
from models.explanations import ExplanationRequest
from services.explanations import DEFAULT_HISTORY, load_history, load_sources, submit_explanation, review_explanation

RUNTIME_DIRECTORY = Path('data/runtime')
HISTORY_PATH = DEFAULT_HISTORY


def _clear():
    st.session_state.pop('explanation_result', None)


def _render_result(result, *, controls=False):
    st.caption(f"Evidence: {result['evidence_status']} · AI assistance: {result['ai_status']}")
    review = result.get('review_status','NOT_REQUIRED')
    if review == 'REJECTED':
        st.warning('The operator rejected this explanation; it is retained only as a review record.')
        return
    if review == 'PENDING':
        st.warning('This high-risk, incomplete or policy-sensitive explanation is awaiting Human Founder/Operator review.')
        if controls and st.session_state.get('explanation_operator'):
            with st.expander('Demo operator evidence preview'):
                for fact in result['facts']:
                    st.write(fact['text'])
                    st.caption(', '.join(fact['source_fields']))
            for approved,label in ((True,'Approve factual explanation'),(False,'Reject explanation')):
                if st.button(label,key='explanation-review-'+str(approved)):
                    try:
                        st.session_state.explanation_result = review_explanation(result['request']['request_id'],approved=approved,operator_role='Human Founder/Operator',history_path=HISTORY_PATH)
                        st.rerun()
                    except (ValueError,OSError):
                        st.error('Review could not be saved or this request was already reviewed.')
        return
    if review == 'APPROVED':
        st.caption('Reviewed and approved by the local demo Human Founder/Operator.')
    for fact in result['facts']:
        st.write(fact['text'])
        st.caption('Evidence: ' + ', '.join(fact['source_fields']))
    with st.expander('Explanation reference'):
        st.json({'request':result['request'], 'trace':result['trace']})


def render_explanations():
    st.markdown('<div class="page-heading"><h1>Decision explanations</h1><p>Ask about a saved decision and inspect its supporting evidence.</p></div>', unsafe_allow_html=True)
    st.caption('Select the exact recorded stage. Requests do not execute actions. AI can organize evidence cards; factual wording stays tied to the record.')
    st.caption('Single-household local demo: the person operating this app is the authorized household operator. Multi-user identity verification is outside this prototype.')
    st.checkbox('Show demo Human Founder/Operator review controls',key='explanation_operator')
    try:
        sources = load_sources(RUNTIME_DIRECTORY)
    except (OSError,UnicodeError):
        st.error('Saved decisions could not be read. Check local storage permissions.')
        return
    if sources:
        # Digest distinguishes initial/resumed stages sharing an event ID.
        by_id = {f"{s['source']}:{s['line']}:{s['sha256']}":s for s in sources}
        selected = st.selectbox('Saved decision', list(by_id), format_func=lambda key: f"{by_id[key]['domain'].replace('_',' ')} · {by_id[key]['event_id'][:8]} · {by_id[key]['source']} line {by_id[key]['line']}", key='explanation_source', on_change=_clear)
        question = st.text_input('What would you like explained?', value='Why was this decision made?', max_chars=300, key='explanation_question', on_change=_clear)
        style = st.selectbox('Explanation detail', ['Detailed','Simpler'],key='explanation_style',on_change=_clear)
        use_ai = st.toggle('Use campus AI to organize the explanation', key='explanation_use_ai', on_change=_clear)
        if use_ai and not os.getenv('ELEC5620_API_KEY', '').strip():
            st.caption('Campus AI is not configured. A factual explanation will use the local fallback.')
        if st.button('Explain saved decision', key='request-explanation', type='primary', disabled=not question.strip()):
            source = by_id[selected]
            provider = None
            ai_missing = use_ai and not os.getenv('ELEC5620_API_KEY','').strip()
            if use_ai and not ai_missing:
                from services.campus_proxy import CampusProxyConfig, propose_explanation_order
                config = CampusProxyConfig.from_environment()
                provider = lambda payload: propose_explanation_order(payload, config)
            try:
                # Re-read before use: never explain a stale selection after the source changed.
                refreshed = load_sources(RUNTIME_DIRECTORY)
                record = next((s['record'] for s in refreshed if s['source']==source['source'] and s['line']==source['line'] and s['sha256']==source['sha256']), None)
                request = ExplanationRequest(str(uuid4()), source['event_id'], source['sha256'], question.strip(), 'brief' if style == 'Simpler' else 'detailed')
                if ai_missing:
                    def provider(_):
                        raise RuntimeError('AI configuration unavailable')
                result = submit_explanation(request, record, history_path=HISTORY_PATH, proposal_provider=provider)
                st.session_state.explanation_result = result.to_dict()
            except OSError:
                _clear()
                st.error('Explanation could not be saved. Check local storage permissions.')
        saved = st.session_state.get('explanation_result')
        if saved and saved['request']['source_sha256'] == by_id[selected]['sha256']:
            _render_result(saved,controls=True)
    else:
        st.info('No stored decisions yet. Run a domain scenario first, then return here.')
    st.subheader('Previous explanation requests')
    try:
        for item in load_history(HISTORY_PATH):
            with st.expander(f"{item['request'].get('question','Explanation')} · {item.get('recorded_at','')} · {item.get('domain','unknown')}"):
                _render_result(item)
    except (OSError,UnicodeError):
        st.warning('Explanation history could not be read.')
