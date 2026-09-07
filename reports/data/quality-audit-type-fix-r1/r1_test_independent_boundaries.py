"""Original CPU review probes: inert data, no external operations or real corpus."""

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'reports/data/quality-audit-r1'))
import audit_sample
import semantic_view
import summarize_reviews
import verify_semantic_views
from toolalign.contracts import canonical_hash, validate_record


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded(value) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def example(tag):
    value = json.loads((REPO / 'tests/fixtures/contracts/example.json').read_text())
    value['example_id'] = 'original-review-' + tag
    value['source_record_hash'] = canonical_hash(['independent-original', tag])
    value['tools'][0]['parameters_json_schema'] = {
        'type': 'object', 'properties': {'query': {'type': 'string', 'maxLength': 64}},
        'required': ['query'], 'additionalProperties': False,
    }
    value['expected_action']['tool_calls'][0]['arguments'] = {'query': 'fixture'}
    return value


def config():
    return {
        'sampling': {'rank_domain': 'toolalign.quality-review.v1', 'seed': 42},
        'patterns': [
            {'name': 'conditional_history', 'user_text_regex': r'\b(if|unless|only after|provided that)\b', 'or_valid_decision_count_greater_than': 1},
            {'name': 'identifier_scope', 'invoked_parameter_name_suffix_regex': r'(id|slug|symbol|code)$'},
            {'name': 'unit_or_encoding', 'invoked_parameter_name_or_description_regex': r'\b(rate|percent|percentage|unit|units|currency|sort|direction|page)\b'},
            {'name': 'relative_time', 'user_text_regex': r'\b(today|tomorrow|yesterday|recent|current|next|last|this)\b'},
            {'name': 'parallel_object', 'maximum_expected_tool_calls_at_least': 3},
            {'name': 'optional_arguments'},
        ],
    }


def assignment(value, index):
    return {k: value[k] for k in ('source_record_hash', 'group_id', 'split')} | {'source_index': index}


def packet(tag, observation=True, normalized_observation=True, two_decisions=False):
    e = example(tag)
    e['tools'][0]['parameters_json_schema']['properties']['flag'] = {'type': 'boolean'}
    e['expected_action']['tool_calls'][0]['arguments']['flag'] = False
    before = copy.deepcopy(e['expected_action']['tool_calls'])
    before[0]['call_id'] = 'history-call'
    e['messages'].extend([
        {'role': 'assistant', 'content': '', 'tool_calls': before, 'tool_call_id': None},
        {'role': 'tool', 'content': encoded({'ok': normalized_observation}), 'tool_calls': [], 'tool_call_id': 'history-call'},
    ])
    validate_record(e, 'example')
    tools = [{'name': t['name'], 'description': t['description'], 'parameters': t['parameters_json_schema']} for t in e['tools']]
    raw_tools = encoded(tools)
    source = {'system': 'Original inert schema\n' + raw_tools + '\nEnd schema', 'conversations': [
        {'from': 'user', 'value': e['messages'][0]['content']},
        {'from': 'assistant', 'value': encoded(before)},
        {'from': 'tool', 'value': encoded([{'results': {'ok': observation}}])},
        {'from': 'assistant', 'value': encoded(e['expected_action'])},
    ]}
    span = [len('Original inert schema\n'), len('Original inert schema\n') + len(raw_tools)]
    source_hash = canonical_hash(source)
    e['source_record_hash'] = source_hash
    decisions = [{'example': e, 'lineage': {'source_turn_index': 3, 'prefix_turn_end_exclusive': 3,
                 'source_action_sha256': hashlib.sha256(source['conversations'][3]['value'].encode()).hexdigest(),
                 'system_conversion': {'schema_span': span}}}]
    if two_decisions:
        second = copy.deepcopy(decisions[0])
        second['example']['expected_action']['tool_calls'][0]['call_id'] = 'next-call'
        second['example']['messages'].extend([
            {'role': 'assistant', 'content': '', 'tool_calls': copy.deepcopy(e['expected_action']['tool_calls']), 'tool_call_id': None},
            {'role': 'tool', 'content': encoded({'ok': True}), 'tool_calls': [], 'tool_call_id': 'call-1'},
        ])
        second['lineage']['source_turn_index'] = 5
        second['lineage']['prefix_turn_end_exclusive'] = 5
        target = encoded(second['example']['expected_action'])
        second['lineage']['source_action_sha256'] = hashlib.sha256(target.encode()).hexdigest()
        source['conversations'].extend([
            {'from': 'tool', 'value': encoded([{'results': {'ok': True}}])},
            {'from': 'assistant', 'value': target},
        ])
        decisions.append(second)
    source_hash = canonical_hash(source)
    for decision in decisions:
        normalized = decision['example']
        normalized['source_record_hash'] = source_hash
        normalized['example_id'] = canonical_hash({k: v for k, v in normalized.items() if k not in ('example_id', 'group_id', 'split')})
        validate_record(normalized, 'example')
    identity = {'source_index': 0, 'source_record_hash': source_hash, 'split': 'train',
                'group_id': e['group_id'], 'valid_decision_count': len(decisions),
                'example_ids': [d['example']['example_id'] for d in decisions]}
    return {'identity': identity, 'source': source, 'valid_decisions': decisions}


def view_fixture(tmp_path, name, value):
    source = tmp_path / 'frozen/packets' / (name + '.json')
    save(source, value)
    view, coverage = semantic_view.render([source])
    target = tmp_path / 'views/fixture.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(view)
    save(target.with_suffix('.json'), {'view_sha256': digest(target), 'coverage': coverage})
    return target, source.parent, coverage


def rehash_view(path):
    metadata = json.loads(path.with_suffix('.json').read_text())
    metadata['view_sha256'] = digest(path)
    save(path.with_suffix('.json'), metadata)


def test_uncalled_schemas_and_invalid_decisions_do_not_trigger_selection():
    good = example('invoked-scope')
    unused = copy.deepcopy(good['tools'][0])
    unused['name'] = 'unused_fixture'
    unused['parameters_json_schema'] = {'type': 'object', 'properties': {
        'symbol': {'type': 'string', 'maxLength': 64}, 'page': {'type': 'number', 'description': 'Percentage rate'},
    }, 'additionalProperties': False}
    good['tools'].append(unused)
    validate_record(good, 'example')
    invalid = copy.deepcopy(good)
    invalid['example_id'] += '-invalid'
    invalid['messages'][0]['content'] = 'Only after tomorrow, use the optional unit.'
    invalid['expected_action']['tool_calls'] *= 3
    invalid['expected_action']['tool_calls'][0]['arguments'] = {}
    pool, _, valid, rejected = audit_sample.index_sources(
        {'train': [good, invalid]}, [assignment(good, 9)], set(), config(),
    )
    assert pool[good['source_record_hash']]['pattern_hits'] == []
    assert len(valid[good['source_record_hash']]) == len(rejected) == 1


def test_duplicate_physical_sources_keep_all_unique_decisions():
    first, second = example('duplicate-source'), example('second-decision')
    second['source_record_hash'] = first['source_record_hash']
    pool, _, _, _ = audit_sample.index_sources(
        {'train': [first, second]}, [assignment(first, 8), assignment(first, 11)], set(), config(),
    )
    assert len(pool) == 1
    row = pool[first['source_record_hash']]
    assert row['source_indices'] == [8, 11] and row['valid_decision_count'] == 2
    assert row['example_ids'] == sorted([first['example_id'], second['example_id']])


def test_observation_reference_preserves_boolean_type(tmp_path):
    value = packet('boolean-observation', observation=0, normalized_observation=False)
    view, packets, _ = view_fixture(tmp_path, 'fixture', value)
    assert verify_semantic_views.verify(view, packets)['sources'] == 1
    tool_message = next(json.loads(line.split(' ', 2)[2]) for line in view.read_text().splitlines()
                        if line.startswith('NORMALIZED_MESSAGE ') and json.loads(line.split(' ', 2)[2])['role'] == 'tool')
    if isinstance(tool_message['content'], dict):
        # The rendered reference points to raw ok=0. Normalized ok=false must
        # remain visible as a distinct JSON value for the semantic reviewer.
        actual = json.loads(value['source']['conversations'][2]['value'])[0]['results']
    else:
        actual = json.loads(tool_message['content'])
    expected = json.loads(value['valid_decisions'][0]['example']['messages'][2]['content'])
    assert encoded(actual) == encoded(expected)


def test_schema_delta_retains_boolean_enum_change():
    before = {'parameters': {'properties': {'flag': {'type': 'integer', 'enum': [0]}}}}
    after = {'parameters': {'properties': {'flag': {'type': 'boolean', 'enum': [False]}}}}
    assert semantic_view.delta(before, after) == [
        ['replace', '/parameters/properties/flag/enum', [False]],
        ['replace', '/parameters/properties/flag/type', 'boolean'],
    ]


def test_verifier_rejects_changed_target_boolean(tmp_path):
    view, packets, _ = view_fixture(tmp_path, 'fixture', packet('target-boolean'))
    assert verify_semantic_views.verify(view, packets)['decisions'] == 1
    lines = view.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith('TARGET '):
            target = json.loads(line.removeprefix('TARGET '))
            target['expected_action']['tool_calls'][0]['arguments']['flag'] = 0
            lines[i] = 'TARGET ' + encoded(target)
    view.write_text('\n'.join(lines) + '\n')
    rehash_view(view)
    with pytest.raises(AssertionError):
        verify_semantic_views.verify(view, packets)


def test_verifier_rejects_missing_second_target(tmp_path):
    view, packets, _ = view_fixture(tmp_path, 'fixture', packet('coverage', two_decisions=True))
    assert verify_semantic_views.verify(view, packets)['decisions'] == 2
    lines = view.read_text().splitlines()
    removed = next(i for i in reversed(range(len(lines))) if lines[i].startswith('TARGET '))
    lines.pop(removed)
    view.write_text('\n'.join(lines) + '\n')
    rehash_view(view)
    with pytest.raises(AssertionError):
        verify_semantic_views.verify(view, packets)


def test_verifier_rejects_source_packet_replacement(tmp_path):
    view, packets, _ = view_fixture(tmp_path, 'fixture', packet('source-binding'))
    value = json.loads((packets / 'fixture.json').read_text())
    value['source']['conversations'][0]['value'] = 'A different original synthetic request.'
    save(packets / 'fixture.json', value)
    with pytest.raises(AssertionError):
        verify_semantic_views.verify(view, packets)


@pytest.mark.parametrize('corruption', ['source_identity', 'target_identity', 'duplicate_target'])
def test_aggregation_rejects_identity_and_coverage_mismatch(tmp_path, corruption):
    value = packet('aggregate-coverage', two_decisions=True)
    view, packets, _ = view_fixture(tmp_path, 'fixture', value)
    identity = value['identity']
    judgment = {**{k: identity[k] for k in ('source_index', 'source_record_hash', 'split', 'group_id')},
                'packet': 'fixture', 'packet_sha256': digest(packets / 'fixture.json'),
                'view': view.name, 'view_sha256': digest(view), 'reviewer': 'Codex-AI(E1)',
                'reviewed_at_utc': '2026-09-07T00:00:00+00:00', 'complete_source_reviewed': True,
                'all_valid_decisions_reviewed': True, 'old_verdict_consulted': False,
                'source_verdict': 'pass', 'decisions': [
                    {'turn': d['lineage']['source_turn_index'], 'example_id': d['example']['example_id'],
                     'source_action_sha256': d['lineage']['source_action_sha256'],
                     'prefix_turn_end_exclusive': d['lineage']['prefix_turn_end_exclusive'],
                     'full_prefix_reviewed': True, 'basis': 'Original synthetic fixture only.',
                     'verdict': 'pass', 'issues': []} for d in value['valid_decisions']]}
    save(tmp_path / 'judgments/fixture.json', judgment)
    assert summarize_reviews.load_record(tmp_path, 'fixture', 'fixture', identity)['source_verdict'] == 'pass'
    if corruption == 'source_identity':
        judgment['source_record_hash'] = 'wrong-source'
    elif corruption == 'target_identity':
        judgment['decisions'][0]['example_id'] = 'wrong-target'
    else:
        judgment['decisions'][1] = copy.deepcopy(judgment['decisions'][0])
    save(tmp_path / 'judgments/fixture.json', judgment)
    with pytest.raises(AssertionError):
        summarize_reviews.load_record(tmp_path, 'fixture', 'fixture', identity)
