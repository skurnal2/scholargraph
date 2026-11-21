import torch.nn as nn


class TinyFormer(nn.Module):
    def __init__(self, vocab_size, num_classes, num_layers=6, num_heads=8,
                 hidden_size=256, ff_size=1024, dropout=0.1):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_size)
        layer = nn.TransformerEncoderLayer(hidden_size, num_heads, ff_size, dropout)
        self.encoder = nn.TransformerEncoder(layer, num_layers)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, tokens):
        x = self.encoder(self.embed(tokens))
        return self.classifier(x.mean(dim=1))
