"""Strict portable configuration; approvals and secret values are never config fields."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .native import BEHAVIOR_COMMIT, RPENT_COMMIT, check_source

PositiveInt = Annotated[int, Field(gt=0, strict=True)]


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Runtime(Config):
    python: Path
    source: Path
    pythonpath: tuple[Path, ...] = ()


class PolicyRuntime(Runtime):
    checkpoint: Path
    manifest: Path


class ModelConfig(Config):
    # This is the historical experiment route, not a current availability claim.
    model: Literal["openai/gpt-6-astra"] = "openai/gpt-6-astra"
    provider: Literal["openai/flex"] = "openai/flex"
    api_key_env: str = Field(default="OPENROUTER_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$")
    expected_prompt_usd_per_token: Literal["0.000005"] = "0.000005"
    expected_completion_usd_per_token: Literal["0.000025"] = "0.000025"


class Campaign(Config):
    journal: Path
    max_calls: PositiveInt = 36
    max_microusd: PositiveInt = 6_000_000


class ExperimentConfig(Config):
    schema_version: Literal[1] = 1
    native: Runtime
    rpc_source: Path
    corvid: PolicyRuntime
    behavior_skill: PolicyRuntime
    hf_cache: Path
    openpi_cache: Path
    campaign: Campaign
    model: ModelConfig = Field(default_factory=ModelConfig)
    simulator_gpu: Annotated[int, Field(ge=0, strict=True)] = 0
    policy_gpu: Annotated[int, Field(ge=0, strict=True)] = 1
    port: Annotated[int, Field(ge=1024, le=65535, strict=True)] = 8011

    @model_validator(mode="after")
    def distinct_gpus(self):
        if self.simulator_gpu == self.policy_gpu:
            raise ValueError("The frozen pair requires separate simulator and policy GPUs")
        return self


def load_config(path):
    path = Path(path).resolve(strict=True)
    value = ExperimentConfig.model_validate_json(path.read_text())
    # Every filesystem path is relative to the config, never the invoking cwd.
    def absolute(model):
        updates = {}
        for key, field in type(model).model_fields.items():
            item = getattr(model, key)
            if isinstance(item, Path):
                updates[key] = (path.parent / item).resolve()
            elif isinstance(item, BaseModel):
                updates[key] = absolute(item)
            elif isinstance(item, tuple):
                updates[key] = tuple((path.parent / p).resolve() for p in item)
        return model.model_copy(update=updates)
    return absolute(value)


def check_runtime(config):
    from .behavior_skill import SOURCE_COMMIT as SKILL_COMMIT
    from .corvid_server import SOURCE_COMMIT as CORVID_COMMIT

    for runtime, pin in ((config.native, BEHAVIOR_COMMIT),
                         (config.corvid, CORVID_COMMIT),
                         (config.behavior_skill, SKILL_COMMIT)):
        if not runtime.python.is_file():
            raise ValueError("Configured Python executable missing")
        check_source(runtime.source, pin)
        if not all(p.is_dir() for p in runtime.pythonpath):
            raise ValueError("Configured import directory missing")
    check_source(config.rpc_source, RPENT_COMMIT)
    for runtime in (config.corvid, config.behavior_skill):
        if not runtime.checkpoint.is_dir() or not runtime.manifest.is_file():
            raise ValueError("Explicit checkpoint and manifest required")
    if not config.hf_cache.is_dir() or not config.openpi_cache.is_dir():
        raise ValueError("Offline model caches must be provisioned explicitly")
