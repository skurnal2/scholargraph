import torch

from models.tinyformer import TinyFormer


def test_optimizer_step_runs():
    # Small smoke test: one optimizer step on random data
    model = TinyFormer(vocab_size=100, num_classes=2, num_layers=1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    tokens = torch.randint(0, 100, (4, 8))
    loss = model(tokens).sum()
    loss.backward()
    optimizer.step()
