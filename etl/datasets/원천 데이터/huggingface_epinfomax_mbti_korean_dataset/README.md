---
dataset_info:
  features:
  - name: text
    dtype: string
  - name: label
    dtype: int64
  splits:
  - name: train
    num_bytes: 2040055
    num_examples: 14564
  - name: validation
    num_bytes: 256786
    num_examples: 1820
  - name: test
    num_bytes: 257793
    num_examples: 1821
  download_size: 1550368
  dataset_size: 2554634
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
  - split: validation
    path: data/validation-*
  - split: test
    path: data/test-*
---
