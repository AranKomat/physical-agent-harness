"""Frozen shadow-grounding configuration; hashes checked against HF revision metadata."""

import hashlib

MODEL = "IDEA-Research/grounding-dino-tiny"
REVISION = "a2bb814dd30d776dcf7e30523b00659f4f141c71"
ONLINE_PROMPT = "a radio. a television. a robot gripper."
FILES = {
    "model.safetensors": "1a2412ef99bd74bcd3c2a246fa1e48581f8889a1300c9051974741314fc042f3",
    "config.json": "eec82c5ab66e16df12a9a212e68ac011779927c2536cf9078658e35d85f0c67a",
    "preprocessor_config.json": "8454179ba95e2ad22947835aad7b45862a601fc0055ab88bf1ee70892d3aea60",
    "tokenizer_config.json": "d40ab645b68211910b9170d22433d43186a6ec8ee6fd10ba170524b25bf4fb56",
    "tokenizer.json": "d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66",
    "added_tokens.json": "909e96cb32d92ce728a01bc99850cbba26196d74115c17ebeb019275412588f2",
    "special_tokens_map.json": "b6d346be366a7d1d48332dbc9fdf3bf8960b5d879522b7799ddba59e76237ee3",
    "vocab.txt": "07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3",
}
ROBOT_FILES = {
    "native_r1pro_processed.urdf": "b0d76760cbedfbcbe1ddc280380dd5f497bbca380313bc096d7239a2c50dae61",
    "native_r1pro_source_cfg.yaml": "d3eb97811138d00edd83bc2be23f8d1d2e2b17c1bbea237a7cf2f9f89752524e",
}


def verify_files(checkpoint, expected=None):
    expected = FILES if expected is None else expected
    for name, digest in expected.items():
        with (checkpoint / name).open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != digest:
                raise ValueError("Grounding snapshot content mismatch: " + name)
    unexpected = {p.name for p in checkpoint.iterdir()} - set(expected) - {"README.md", ".gitattributes"}
    if unexpected:
        raise ValueError("Unexpected grounding snapshot contents")
    return dict(expected)


def online_identity():
    return {"model": MODEL, "revision": REVISION, "prompt": ONLINE_PROMPT,
            "box_threshold": .4, "text_threshold": .3,
            "weights_sha256": FILES["model.safetensors"], "files_sha256": dict(FILES),
            "robot_self_check": {"assets_sha256": dict(ROBOT_FILES),
                "eef_ambiguity_radius_m": .18,
                "scope": "reject_near_hand_ambiguity_not_full_robot_segmentation"}}


def validate_online_identity(identity):
    if not isinstance(identity, dict) or any(identity.get(k) != v for k, v in online_identity().items()):
        raise ValueError("Grounding service does not match frozen online configuration")
