import h5py
import json
from strap.utils.retrieval_utils import TrajectoryMatchResult, RetrievalArgs
from strap.utils.file_utils import DatasetConfig, get_demo_grp
import numpy as np


def get_libero_lang_instruction(f: h5py.File, demo_key) -> str:
    return json.loads(f["data"].attrs["problem_info"]).get("language_instruction", "dummy")


def save_trajectory_result_libero(data_grp: h5py.File, out_grp: h5py.File, result: TrajectoryMatchResult, args: RetrievalArgs, dataset_config: DatasetConfig, new_demo_key: str):
    language_instruction = get_libero_lang_instruction(data_grp, result.file_traj_key)
    data_grp = get_demo_grp(data_grp, dataset_config.file_structure.demo_group)
    data_grp.copy(result.file_traj_key, dest=out_grp, name=new_demo_key)
    max_length = len(data_grp[result.file_traj_key][dataset_config.file_structure.obs_action_group])
    extra_start = max(0, 0 - result.start + args.frame_stack - 1)  # we want to pad by 4 if the frame stack is 5
    extra_end = max(0, result.end - max_length + args.action_chunk - 1)

    start_idx = max(0, result.start - args.frame_stack)
    end_idx = min(result.end + args.action_chunk, max_length)

    for lk in ["actions", "states"]:
        tmp_copy = np.array(out_grp[new_demo_key][lk][start_idx:end_idx]).copy()
        # pad the start if needed
        if extra_start:
            tmp_copy = np.concatenate([np.stack([tmp_copy[0] for i in range(extra_start)], axis=0), tmp_copy], axis=0)
        # pad the end if needed
        if extra_end:
            tmp_copy = np.concatenate([tmp_copy, np.stack([tmp_copy[-1] for i in range(extra_end)], axis=0)], axis=0)
        del out_grp[new_demo_key][lk]
        out_grp[new_demo_key][lk] = tmp_copy

    for lk in out_grp[new_demo_key]["obs"].keys():
        tmp_copy = np.array(out_grp[new_demo_key]["obs"][lk][start_idx:end_idx]).copy()
        if extra_start:
            tmp_copy = np.concatenate([np.stack([tmp_copy[0] for i in range(extra_start)], axis=0), tmp_copy], axis=0)
        # pad the end if needed
        if extra_end:
            tmp_copy = np.concatenate([tmp_copy, np.stack([tmp_copy[-1] for i in range(extra_end)], axis=0)], axis=0)
        del out_grp[new_demo_key]["obs"][lk]
        out_grp[new_demo_key]["obs"][lk] = tmp_copy

        # coppy the attributes
        for attr_name, attr_value in data_grp[result.file_traj_key].attrs.items():
            out_grp[new_demo_key].attrs[attr_name] = attr_value
        out_grp[new_demo_key].attrs["num_samples"] = len(out_grp[new_demo_key]["actions"])
        out_grp[new_demo_key].attrs["ep_meta"] = json.dumps({"lang": language_instruction})
