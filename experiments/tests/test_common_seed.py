import random

import torch

from experiments.common import set_global_seed


def test_set_global_seed_reproducible_for_python_and_torch():
    set_global_seed(123)
    py1 = random.random()
    torch1 = torch.randn(4)

    set_global_seed(123)
    py2 = random.random()
    torch2 = torch.randn(4)

    assert py1 == py2
    assert torch.allclose(torch1, torch2)


def test_set_global_seed_reproducible_for_numpy_if_available():
    np = __import__("numpy")
    set_global_seed(456)
    arr1 = np.random.rand(5)

    set_global_seed(456)
    arr2 = np.random.rand(5)

    assert np.allclose(arr1, arr2)

