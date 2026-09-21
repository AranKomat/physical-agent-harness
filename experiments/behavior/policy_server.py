"""Pinned RPent loopback RPC only; no private campaign or model dependency."""

import os
from pathlib import Path

from rpent.utils.rpc import http_rpc
from rpent.utils.rpc.http_rpc import HttpRpcClient
from rpent.utils.rpc.rpc_facade import RpcFacade

from .native import RPENT_COMMIT, check_source

root = Path(os.environ["BEHAVIOR_RPC_SOURCE"]).resolve(strict=True)
check_source(root, RPENT_COMMIT)
if root not in Path(http_rpc.__file__).resolve().parents:
    raise ValueError("Imported RPC is not the configured pinned source")


class PolicyFacade(RpcFacade):
    def __init__(self, backend):
        super().__init__()
        self._rpc = {"policy.reset": backend.reset, "policy.infer": backend.infer}


class HttpPolicyTransport:
    def __init__(self, port=8011, timeout_s=90):
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid loopback port")
        self.client = HttpRpcClient(f"http://127.0.0.1:{port}", enable_sessions=False)
        self.timeout_s = timeout_s

    def reset(self, stamp):
        return self.client.call("policy.reset", args=(stamp,), timeout_s=self.timeout_s)

    def infer(self, packet):
        return self.client.call("policy.infer", args=(packet,), timeout_s=self.timeout_s)
