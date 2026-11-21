from torch.optim.lr_scheduler import LambdaLR


def warmup_scheduler(optimizer, warmup_steps):
    # Linear warmup, then constant learning rate
    return LambdaLR(optimizer, lambda step: min(1.0, (step + 1) / warmup_steps))
