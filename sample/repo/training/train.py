import torch
from torch.utils.data import DataLoader

from models.losses import build_loss
from models.tinyformer import TinyFormer
from utils.schedule import warmup_scheduler


def train(dataset, vocab_size, num_classes, epochs=10):
    model = TinyFormer(vocab_size, num_classes)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=0.01)
    scheduler = warmup_scheduler(optimizer, warmup_steps=4000)
    loss_fn = build_loss()

    for epoch in range(epochs):
        for tokens, labels in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(tokens), labels)
            loss.backward()
            optimizer.step()
            scheduler.step()
