import torch.nn as nn


def build_loss():
    # Cross-entropy loss for classification
    return nn.CrossEntropyLoss(label_smoothing=0.0)
