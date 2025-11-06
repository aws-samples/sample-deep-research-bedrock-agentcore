"""S3 Uploader utility for research outputs

Uploads final research reports (markdown and Word documents) to S3
using session_id as the key prefix for organization.
"""

import os
import boto3
from pathlib import Path
from typing import Dict, Optional
from botocore.exceptions import ClientError


class S3Uploader:
    """Handles uploading research outputs to S3"""
    
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize S3 uploader
        
        Args:
            bucket_name: S3 bucket name (defaults to env var S3_OUTPUTS_BUCKET)
            region: AWS region (defaults to env var AWS_REGION)
        """
        self.bucket_name = bucket_name or os.getenv('S3_OUTPUTS_BUCKET')
        self.region = region or os.getenv('AWS_REGION', 'us-west-2')
        
        if not self.bucket_name:
            raise ValueError("S3_OUTPUTS_BUCKET environment variable not set")
        
        self.s3_client = boto3.client('s3', region_name=self.region)
    
    def upload_report(self,
                     session_id: str,
                     file_path: str,
                     file_type: str = 'docx',
                     version: str = 'draft') -> Dict[str, str]:
        """
        Upload research report to S3

        Args:
            session_id: Research session ID
            file_path: Local file path
            file_type: File type ('docx', 'md', or 'pdf')
            version: Version name (defaults to 'draft')

        Returns:
            Dict with s3_key and s3_uri
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # S3 key format: research-outputs/{session_id}/versions/{version}/report.{ext}
        s3_key = f"research-outputs/{session_id}/versions/{version}/report.{file_type}"
        
        # Determine content type
        content_types = {
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'md': 'text/markdown',
            'pdf': 'application/pdf'
        }
        content_type = content_types.get(file_type, 'application/octet-stream')
        
        try:
            print(f"\n📤 Uploading {file_type.upper()} to S3...")
            print(f"   Bucket: {self.bucket_name}")
            print(f"   Key: {s3_key}")
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            print(f"   ✅ Upload successful: {s3_uri}")
            
            return {
                's3_key': s3_key,
                's3_uri': s3_uri,
                'bucket': self.bucket_name,
                'region': self.region
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            print(f"   ❌ S3 upload failed ({error_code}): {error_msg}")
            raise
    
    def upload_dimension_documents(self,
                                   session_id: str,
                                   dimension_documents: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """
        Upload all dimension markdown documents to S3
        
        Args:
            session_id: Research session ID
            dimension_documents: Dict mapping dimension name to file path
        
        Returns:
            Dict mapping dimension name to S3 info
        """
        uploaded = {}
        
        for dimension, file_path in dimension_documents.items():
            if not Path(file_path).exists():
                print(f"   ⚠️  Skipping missing dimension document: {dimension}")
                continue
            
            # S3 key format: research-outputs/{session_id}/dimensions/{dimension}.md
            safe_dimension = dimension.replace('/', '_').replace(' ', '_')
            s3_key = f"research-outputs/{session_id}/dimensions/{safe_dimension}.md"
            
            try:
                self.s3_client.upload_file(
                    file_path,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'text/markdown',
                        'ServerSideEncryption': 'AES256'
                    }
                )
                
                uploaded[dimension] = {
                    's3_key': s3_key,
                    's3_uri': f"s3://{self.bucket_name}/{s3_key}",
                    'bucket': self.bucket_name
                }
                
            except ClientError as e:
                print(f"   ⚠️  Failed to upload {dimension}: {e}")
        
        if uploaded:
            print(f"   ✅ Uploaded {len(uploaded)} dimension documents to S3")
        
        return uploaded


def upload_research_outputs(session_id: str,
                            markdown_path: Optional[str] = None,
                            docx_path: Optional[str] = None,
                            pdf_path: Optional[str] = None,
                            dimension_documents: Optional[Dict[str, str]] = None,
                            chart_files: Optional[list] = None,
                            version: str = 'draft') -> Dict[str, any]:
    """
    Upload all research outputs for a session to S3

    Args:
        session_id: Research session ID
        markdown_path: Path to markdown report
        docx_path: Path to Word document report
        pdf_path: Path to PDF report
        dimension_documents: Dict of dimension documents
        chart_files: List of chart file metadata (with 'path', 'title', 'type')
        version: Version name (defaults to 'draft')

    Returns:
        Dict with upload results
    """
    uploader = S3Uploader()
    results = {
        'session_id': session_id,
        'version': version,
        'uploads': {}
    }

    # Upload Word document
    if docx_path and Path(docx_path).exists():
        try:
            results['uploads']['docx'] = uploader.upload_report(session_id, docx_path, 'docx', version)
        except Exception as e:
            print(f"Failed to upload DOCX: {e}")
            results['uploads']['docx'] = {'error': str(e)}

    # Upload PDF document
    if pdf_path and Path(pdf_path).exists():
        try:
            results['uploads']['pdf'] = uploader.upload_report(session_id, pdf_path, 'pdf', version)
        except Exception as e:
            print(f"Failed to upload PDF: {e}")
            results['uploads']['pdf'] = {'error': str(e)}

    # Upload Markdown
    if markdown_path and Path(markdown_path).exists():
        try:
            results['uploads']['markdown'] = uploader.upload_report(session_id, markdown_path, 'md', version)
        except Exception as e:
            print(f"Failed to upload Markdown: {e}")
            results['uploads']['markdown'] = {'error': str(e)}
    
    # Upload dimension documents
    if dimension_documents:
        try:
            results['uploads']['dimensions'] = uploader.upload_dimension_documents(
                session_id, dimension_documents
            )
        except Exception as e:
            print(f"Failed to upload dimension documents: {e}")
            results['uploads']['dimensions'] = {'error': str(e)}

    # Upload chart files
    if chart_files:
        results['uploads']['charts'] = []
        for chart in chart_files:
            chart_path = chart.get('path')
            chart_title = chart.get('title', 'chart')
            chart_type = chart.get('type', 'unknown')

            if chart_path and Path(chart_path).exists():
                try:
                    # Use original filename from path (preserves exact filename used in markdown)
                    original_filename = Path(chart_path).name

                    # S3 key: research-outputs/{session_id}/charts/{filename}.png
                    s3_key = f"research-outputs/{session_id}/charts/{original_filename}"

                    # Upload using s3_client directly with custom key
                    uploader.s3_client.upload_file(
                        chart_path,
                        uploader.bucket_name,
                        s3_key,
                        ExtraArgs={
                            'ContentType': 'image/png',
                            'ServerSideEncryption': 'AES256'
                        }
                    )

                    s3_uri = f"s3://{uploader.bucket_name}/{s3_key}"
                    results['uploads']['charts'].append({
                        'title': chart_title,
                        'type': chart_type,
                        's3_key': s3_key,
                        's3_uri': s3_uri
                    })
                    print(f"   ✅ Chart uploaded: {chart_title} → {s3_uri}")

                except Exception as e:
                    print(f"   ⚠️  Failed to upload chart '{chart_title}': {e}")
                    results['uploads']['charts'].append({
                        'title': chart_title,
                        'error': str(e)
                    })

    return results
