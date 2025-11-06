#!/usr/bin/env python3
"""
Convert existing DOCX files in S3 to PDF and upload them

This script:
1. Lists all DOCX files in the S3 bucket
2. Downloads each DOCX
3. Converts to PDF using docx2pdf
4. Uploads PDF to the same path structure
"""

import os
import sys
import boto3
import tempfile
from pathlib import Path
from docx2pdf import convert
from botocore.exceptions import ClientError

# Configuration
BUCKET_NAME = os.getenv('S3_OUTPUTS_BUCKET')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')
AWS_PROFILE = os.getenv('AWS_PROFILE', 'shared-account')

if not BUCKET_NAME:
    print("❌ S3_OUTPUTS_BUCKET environment variable not set")
    sys.exit(1)


def list_docx_files(s3_client, bucket):
    """List all DOCX files in the bucket"""
    print(f"📋 Listing DOCX files in s3://{bucket}/research-outputs/...")

    docx_files = []
    paginator = s3_client.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket, Prefix='research-outputs/'):
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('.docx') and '/versions/' in key:
                docx_files.append(key)

    print(f"   Found {len(docx_files)} DOCX files")
    return docx_files


def check_pdf_exists(s3_client, bucket, pdf_key):
    """Check if PDF already exists"""
    try:
        s3_client.head_object(Bucket=bucket, Key=pdf_key)
        return True
    except ClientError:
        return False


def convert_docx_to_pdf_for_s3(s3_client, bucket, docx_key):
    """
    Download DOCX from S3, convert to PDF, upload PDF

    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        docx_key: S3 key for DOCX file (e.g., research-outputs/session-id/versions/draft/report.docx)
    """
    # Generate PDF key (replace .docx with .pdf)
    pdf_key = docx_key.replace('.docx', '.pdf')

    # Check if PDF already exists
    if check_pdf_exists(s3_client, bucket, pdf_key):
        print(f"   ⏭️  PDF already exists: {pdf_key}")
        return True

    print(f"   📥 Processing: {docx_key}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Download DOCX
        docx_path = tmpdir / "report.docx"
        pdf_path = tmpdir / "report.pdf"

        try:
            print(f"      Downloading DOCX...")
            s3_client.download_file(bucket, docx_key, str(docx_path))

            # Convert to PDF
            print(f"      Converting to PDF...")
            convert(str(docx_path), str(pdf_path))

            if not pdf_path.exists():
                raise Exception("PDF conversion failed - file not created")

            # Upload PDF
            print(f"      Uploading PDF...")
            s3_client.upload_file(
                str(pdf_path),
                bucket,
                pdf_key,
                ExtraArgs={
                    'ContentType': 'application/pdf',
                    'ServerSideEncryption': 'AES256'
                }
            )

            print(f"   ✅ Successfully created: {pdf_key}")
            return True

        except Exception as e:
            print(f"   ❌ Failed to convert {docx_key}: {e}")
            return False


def main():
    print("=" * 60)
    print("  Convert Existing DOCX Files to PDF")
    print("=" * 60)
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client('s3')

    print(f"📦 Bucket: {BUCKET_NAME}")
    print(f"🌎 Region: {AWS_REGION}")
    print(f"👤 Profile: {AWS_PROFILE}")
    print()

    # List all DOCX files
    docx_files = list_docx_files(s3_client, BUCKET_NAME)

    if not docx_files:
        print("✨ No DOCX files found")
        return

    print()
    print(f"🔄 Converting {len(docx_files)} files...")
    print()

    # Convert each file
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, docx_key in enumerate(docx_files, 1):
        print(f"[{i}/{len(docx_files)}] {docx_key}")

        pdf_key = docx_key.replace('.docx', '.pdf')
        if check_pdf_exists(s3_client, BUCKET_NAME, pdf_key):
            print(f"   ⏭️  PDF already exists: {pdf_key}")
            skip_count += 1
        elif convert_docx_to_pdf_for_s3(s3_client, BUCKET_NAME, docx_key):
            success_count += 1
        else:
            fail_count += 1

        print()

    # Summary
    print("=" * 60)
    print("  Conversion Summary")
    print("=" * 60)
    print(f"  ✅ Converted: {success_count}")
    print(f"  ⏭️  Skipped (already exists): {skip_count}")
    print(f"  ❌ Failed: {fail_count}")
    print(f"  📊 Total: {len(docx_files)}")
    print()

    if fail_count > 0:
        print("⚠️  Some files failed to convert. Check the logs above.")
        sys.exit(1)
    else:
        print("✨ All done!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
