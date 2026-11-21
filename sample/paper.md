# TinyFormer: A Small Transformer for Text Classification

## Abstract
We present TinyFormer, a compact transformer encoder for sentence classification.
It reaches strong accuracy on the SST-2 benchmark while using under 10M parameters.

## 1. Introduction
Large language models are expensive to train and deploy. We show that a small,
carefully trained encoder is competitive on short-text classification tasks.

## 3. Model Architecture
TinyFormer is a stack of 6 transformer encoder layers. Each layer has 8 attention
heads and a hidden size of 256. The feed-forward inner dimension is 1024.
We apply dropout with probability 0.1 after every sub-layer.

## 4. Training
We train with the AdamW optimizer using a learning rate of 1e-4 and weight decay
of 0.01. The learning rate is warmed up linearly over the first 4000 steps.
We use a batch size of 32 and train for 10 epochs.

## 4.1 Loss Function
The model is trained with cross-entropy loss with label smoothing of 0.1, which
we found reduces overconfidence on ambiguous sentences.

## 5. Results
TinyFormer achieves 91.2% accuracy on SST-2, within 2 points of models 10x larger.
