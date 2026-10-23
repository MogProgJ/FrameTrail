"""Allow only the documented CUDA grid-sampler warning during backward.
Strict deterministic mode is restored before validation or optimizer updates.
This does not guarantee bitwise reproducibility on CUDA.
"""
import warnings
from contextlib import contextmanager
from torch.nn.attention import SDPBackend, sdpa_kernel
import torch

POLICY = dict(attention_backend="MATH-only-for-forward-and-backward",mode="strict-except-grid-sampler-CUDA-backward",
              permitted_warning="grid_sampler_2d_backward_cuda",
              bitwise_reproducibility_guaranteed=False,
              other_backward_warnings="error",
              fixed_seeds_and_gold_stream=True)

def attention_state():
    return {name: getattr(torch.backends.cuda, name + "_sdp_enabled")()
            for name in ("math", "flash", "mem_efficient", "cudnn")}

def assert_math_attention():
    state=attention_state()
    if state != dict(math=True, flash=False, mem_efficient=False, cudnn=False):
        raise RuntimeError("Expected math-only attention throughout forward/backward: " + str(state))
    return state

@contextmanager
def math_attention():
    # Backend selection must happen before forward, when autograd kernels are chosen.
    # Selecting it only inside backward cannot change an already built attention graph.
    with sdpa_kernel(SDPBackend.MATH):
        assert_math_attention()
        yield

def backward(loss):
    assert_math_attention()
    enabled=torch.are_deterministic_algorithms_enabled()
    warn_only=torch.is_deterministic_algorithms_warn_only_enabled()
    if not enabled or warn_only:
        raise RuntimeError("Expected strict deterministic mode before backward")
    try:
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("error")
            warnings.filterwarnings("always", category=UserWarning,
                message=r"^grid_sampler_2d_backward_cuda does not have a deterministic implementation(?:[., ]|$)")
            torch.use_deterministic_algorithms(True,warn_only=True)
            loss.backward()
        return len(observed)
    finally:
        torch.use_deterministic_algorithms(enabled,warn_only=warn_only)
