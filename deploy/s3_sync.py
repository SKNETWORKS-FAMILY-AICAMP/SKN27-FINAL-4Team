# -*- coding: utf-8 -*-
"""S3 → 로컬 단순 동기화 (감정모델 산출물용, ECS 태스크 롤 자격증명 사용).
사용: python s3_sync.py s3://버킷/접두어 /artifacts
aws cli(120MB) 대신 boto3로 — 이미지 경량 유지."""
import os
import sys

import boto3


def main():
    uri, dest = sys.argv[1], sys.argv[2]
    assert uri.startswith('s3://'), f's3:// URI가 아님: {uri}'
    bucket, _, prefix = uri[5:].partition('/')
    s3 = boto3.client('s3')
    paginator = s3.get_paginator('list_objects_v2')
    n = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('/'):
                continue
            rel = os.path.relpath(key, prefix) if prefix else key
            path = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # 크기 같으면 스킵 (재기동 시 재다운로드 방지)
            if os.path.exists(path) and os.path.getsize(path) == obj['Size']:
                continue
            s3.download_file(bucket, key, path)
            n += 1
            print(f'  받음: {rel} ({obj["Size"]:,}B)')
    print(f'동기화 완료 — 새로 받은 파일 {n}개')


if __name__ == '__main__':
    main()
