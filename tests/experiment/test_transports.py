from __future__ import annotations

import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from physical_harness.contracts import SkillRequest
from physical_harness.experiment.native_rpc import ProcessNative
from physical_harness.experiment.transport import HttpTransport, TransportFailure


def test_transport_is_opt_in_and_rejects_nonlocal_cleartext():
    with pytest.raises(ValueError):
        HttpTransport('http://example.com/v1', None, allow_local_http=True)
    with pytest.raises(ValueError):
        HttpTransport('https://user:password@example.com/v1', None)
    transport = HttpTransport('https://example.com/v1', None)
    with pytest.raises(PermissionError):
        transport.post('/responses', {})


def test_actual_http_worker_on_loopback_no_external_service():
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append((self.path, self.rfile.read(int(self.headers['Content-Length']))))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"input_tokens":123}')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = HttpTransport(f'http://127.0.0.1:{server.server_port}/v1', None,
                                  allow_network=True, allow_local_http=True, timeout_s=5)
        assert transport.post('/responses/input_tokens', {'model': 'fixture'}) == {'input_tokens': 123}
        assert len(seen) == 1 and seen[0][0] == '/v1/responses/input_tokens'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_http_failure_is_not_retried_or_echoed():
    seen = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(self.path)
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'secret provider error payload')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        transport = HttpTransport(f'http://127.0.0.1:{server.server_port}/v1', None,
                                  allow_network=True, allow_local_http=True, timeout_s=5)
        with pytest.raises(TransportFailure) as error:
            transport.post('/responses', {})
        assert 'secret' not in str(error.value) and len(seen) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.skipif(os.name != 'posix', reason='IPC supports POSIX only')
def test_actual_native_subprocess_roundtrip():
    command = [sys.executable, '-m', 'physical_harness.experiment', 'serve-native',
               '--factory', 'physical_harness.experiment.fixture:rpc_fixture_factory',
               '--episode', 'ep']
    native = ProcessNative(command, episode='ep', timeout_s=10)
    try:
        before = native.observe()
        receipt = native.run_skill(SkillRequest('s', 'fixture', 'close', max_wall_s=2))
        after = native.observe()
        assert before.sim_time == 0 and after.sim_time == 1
        assert before.cameras[0].data != after.cameras[0].data
        assert receipt.metadata['stop_acknowledged'] is True
        assert native.stop()
    finally:
        native.close()
    assert native.process.poll() is not None


@pytest.mark.skipif(os.name != 'posix', reason='IPC supports POSIX only')
def test_native_hang_poisoned_channel_does_not_fake_stop():
    worker = '''import json,sys,time
r=json.loads(sys.stdin.readline())
print(json.dumps(dict(version=1,episode=r['episode'],id=r['id'],result=dict(name='hang',simulated=True,qualification_id='fixture'),error=None)),flush=True)
sys.stdin.readline()
time.sleep(60)
'''
    native = ProcessNative([sys.executable, '-c', worker], episode='ep', timeout_s=1)
    try:
        with pytest.raises(TimeoutError):
            native.observe()
        assert native.poisoned and native.stop() is False
        with pytest.raises(RuntimeError):
            native.observe()
    finally:
        native.close()
