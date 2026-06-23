# huggingface_jojo0217_korean_safe_conversation

## Source

- Dataset: `jojo0217/korean_safe_conversation`
- URL: https://huggingface.co/datasets/jojo0217/korean_safe_conversation
- License: Apache-2.0
- Language: Korean
- Format: JSONL

## Purpose

This dataset is kept as a Korean conversation validation source. It is not an MBTI-labeled training dataset.

Use it to check whether the service pipeline works on Korean chatbot-like user utterances, especially daily conversation and emotional conversation.

## Files Collected

| file | rows | note |
| --- | ---: | --- |
| `huggingface_jojo0217_korean_safe_conversation__train.jsonl` | 26,979 | integrated training-style conversation data |
| `raw/huggingface_jojo0217_korean_safe_conversation__raw_conversation.jsonl` | 2,063 | daily conversation source |
| `raw/huggingface_jojo0217_korean_safe_conversation__raw_gamseong.jsonl` | 1,020 | emotional conversation source |

## Column Meaning

| column | intended use |
| --- | --- |
| `instruction` | user utterance candidate |
| `output` | assistant/system response candidate |
| `input` | usually empty |
| `id` | present in raw files |

For MBTI service-domain validation, use `instruction` as the user utterance. Do not use `output` for user MBTI inference because it is assistant-style response text.
