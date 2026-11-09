"""Synthetic protocol fixtures only; these are NOT real MiniMax calls."""
import json

import httpx
import pytest

from minimax_sdd.minimax_client import MiniMaxClient, MiniMaxConfig, MiniMaxError


def client(handler):
    return MiniMaxClient(MiniMaxConfig('https://api.minimax.io/v1', 'fixture-secret', 'MiniMax-M3.1-Flash'), transport=httpx.MockTransport(handler))


def response(content='{"files":{"ticket_tool.py":"print(1)\\n"}}', **extra):
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': content, 'reasoning_content': 'PRIVATE THOUGHTS'}}], **extra}


def test_missing_config_never_calls(tmp_path):
    with pytest.raises(MiniMaxError, match='no request was sent'):
        MiniMaxConfig.from_env_file(tmp_path / 'absent.env')


def test_config_and_secret_repr(tmp_path):
    path = tmp_path / 'minimax.env'
    path.write_text('MINIMAX_BASE_URL=https://api.minimax.io/v1\nMINIMAX_API_KEY=fixture-secret\nMINIMAX_MODEL=fixture-model\n')
    config = MiniMaxConfig.from_env_file(path)
    assert 'fixture-secret' not in repr(config)
    assert config.model == 'fixture-model'


@pytest.mark.parametrize('url', ['http://api.minimax.io/v1', 'https://api.minimax.io/anthropic', 'https://key@api.minimax.io/v1', 'https://api.minimax.io/v1?key=x'])
def test_reject_wrong_protocol_url(url):
    with pytest.raises(MiniMaxError):
        MiniMaxClient(MiniMaxConfig(url, 'secret', 'model'))


def test_request_and_reasoning_removal():
    calls = []
    def handler(request):
        calls.append(json.loads(request.content))
        assert request.url.path == '/v1/chat/completions'
        assert request.headers['Authorization'] == 'Bearer fixture-secret'
        return httpx.Response(200, json=response('<think>PRIVATE inline</think> final fixture-secret'))
    result = client(handler).generate('Task', {'spec': 'v2'})
    assert calls[0]['messages'][1]['content'] == json.dumps({'task': 'Task', 'retrieved_context': {'spec': 'v2'}}, ensure_ascii=False)
    assert result['final_content'] == 'final [REDACTED]'
    assert result['source'] == 'fixture'
    assert 'PRIVATE' not in json.dumps(result)
    assert 'fixture-secret' not in json.dumps(result)
    assert calls[0]['max_completion_tokens'] == 16384
    assert calls[0]['reasoning_split'] is True


@pytest.mark.parametrize('status,match', [(401, 'authentication'), (403, 'authentication'), (429, 'rate/quota'), (500, 'HTTP 500')])
def test_safe_errors(status, match):
    with pytest.raises(MiniMaxError, match=match) as error:
        client(lambda _: httpx.Response(status, text='fixture-secret PRIVATE')).check_service()
    assert 'PRIVATE' not in str(error.value)
    assert 'fixture-secret' not in str(error.value)


def test_call_limit():
    c = client(lambda _: httpx.Response(200, json=response('OK')))
    c.check_service()
    c.generate('task', {})
    with pytest.raises(MiniMaxError, match='budget exhausted'):
        c.generate('task', {})


@pytest.mark.parametrize('payload', [{}, {'choices': []}, {'choices': [None]}, {'choices': [{'finish_reason': 'stop', 'message': []}]}, {'choices': [{'finish_reason': 'length', 'message': {'content': 'partial'}}]}, response('<think>unfinished'), response('')])
def test_invalid_response(payload):
    with pytest.raises(MiniMaxError):
        client(lambda _: httpx.Response(200, json=payload)).generate('task', {})


def test_invalid_json():
    with pytest.raises(MiniMaxError, match='invalid JSON'):
        client(lambda _: httpx.Response(200, text='invalid')).check_service()


def test_timeout():
    def handler(request):
        raise httpx.ReadTimeout('fixture-secret', request=request)
    with pytest.raises(MiniMaxError, match='timed out') as error:
        client(handler).check_service()
    assert 'fixture-secret' not in str(error.value)


def test_response_limit():
    with pytest.raises(MiniMaxError, match='byte limit'):
        client(lambda _: httpx.Response(200, content=b'x' * 1_000_001)).check_service()
