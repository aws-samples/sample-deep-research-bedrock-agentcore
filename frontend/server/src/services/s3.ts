import { S3Client, GetObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import { config } from '../config';

const s3Client = new S3Client({ region: config.aws.region });

/**
 * Get file content from S3
 */
export async function getS3FileContent(
  sessionId: string,
  fileType: 'docx' | 'md' | 'pdf',
  version: string = 'draft'
): Promise<string> {
  const bucket = config.s3.outputsBucket;

  if (!bucket) {
    throw new Error('S3 outputs bucket not configured');
  }

  const s3Key = `research-outputs/${sessionId}/versions/${version}/report.${fileType}`;

  const command = new GetObjectCommand({
    Bucket: bucket,
    Key: s3Key,
  });

  try {
    const response = await s3Client.send(command);

    if (!response.Body) {
      throw new Error('Empty response body from S3');
    }

    // Convert stream to string
    const chunks: Uint8Array[] = [];
    for await (const chunk of response.Body as any) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);
    return buffer.toString('utf-8');
  } catch (error: any) {
    console.error(`Failed to get S3 file content: ${error}`);
    throw new Error(`Failed to retrieve file from S3: ${error.message}`);
  }
}

export interface DownloadLink {
  url: string;
  expiresIn: number;
  filename: string;
}

/**
 * Generate presigned URL for a chart image
 */
export async function generateChartImageUrl(
  sessionId: string,
  imagePath: string,
  expiresIn: number = 3600
): Promise<string> {
  const bucket = config.s3.outputsBucket;

  if (!bucket) {
    throw new Error('S3 outputs bucket not configured');
  }

  // Extract filename from path (e.g., "charts/chart1.png" -> "chart1.png")
  const filename = imagePath.split('/').pop() || imagePath;
  const s3Key = `research-outputs/${sessionId}/charts/${filename}`;

  const command = new GetObjectCommand({
    Bucket: bucket,
    Key: s3Key,
  });

  try {
    const url = await getSignedUrl(s3Client, command, { expiresIn });
    return url;
  } catch (error: any) {
    console.error(`Failed to generate chart image URL: ${error}`);
    throw new Error(`Failed to generate image URL: ${error.message}`);
  }
}

/**
 * Get all chart images for a session
 */
export async function getChartImageUrls(
  sessionId: string,
  expiresIn: number = 3600
): Promise<Record<string, string>> {
  const bucket = config.s3.outputsBucket;

  if (!bucket) {
    return {};
  }

  // List all chart files in the session's charts directory
  const prefix = `research-outputs/${sessionId}/charts/`;

  try {
    const listCommand = new ListObjectsV2Command({
      Bucket: bucket,
      Prefix: prefix,
    });

    const response = await s3Client.send(listCommand);
    const imageUrls: Record<string, string> = {};

    if (response.Contents) {
      for (const item of response.Contents) {
        if (item.Key && item.Key.endsWith('.png')) {
          const filename = item.Key.split('/').pop()!;
          const command = new GetObjectCommand({
            Bucket: bucket,
            Key: item.Key,
          });
          const url = await getSignedUrl(s3Client, command, { expiresIn });
          imageUrls[filename] = url;
        }
      }
    }

    return imageUrls;
  } catch (error: any) {
    console.error(`Failed to list chart images: ${error}`);
    return {};
  }
}

/**
 * Generate presigned URL for downloading research output from S3
 */
export async function generatePresignedDownloadUrl(
  sessionId: string,
  fileType: 'docx' | 'md' | 'pdf',
  expiresIn: number = 3600,
  version: string = 'draft'
): Promise<DownloadLink> {
  const bucket = config.s3.outputsBucket;

  if (!bucket) {
    throw new Error('S3 outputs bucket not configured');
  }

  const s3Key = `research-outputs/${sessionId}/versions/${version}/report.${fileType}`;
  const filename = `research_report_${sessionId}_${version}.${fileType}`;

  const command = new GetObjectCommand({
    Bucket: bucket,
    Key: s3Key,
    ResponseContentDisposition: `attachment; filename="${filename}"`,
  });

  const url = await getSignedUrl(s3Client, command, { expiresIn });

  return {
    url,
    expiresIn,
    filename,
  };
}

/**
 * Generate presigned URLs for both markdown and Word document
 */
export async function generateDownloadLinks(
  sessionId: string,
  expiresIn: number = 3600,
  version: string = 'draft'
): Promise<{ markdown?: DownloadLink; docx?: DownloadLink; pdf?: DownloadLink }> {
  const links: { markdown?: DownloadLink; docx?: DownloadLink; pdf?: DownloadLink } = {};

  try {
    links.docx = await generatePresignedDownloadUrl(sessionId, 'docx', expiresIn, version);
  } catch (error) {
    console.warn(`Failed to generate DOCX download link: ${error}`);
  }

  try {
    links.pdf = await generatePresignedDownloadUrl(sessionId, 'pdf', expiresIn, version);
  } catch (error) {
    console.warn(`Failed to generate PDF download link: ${error}`);
  }

  try {
    links.markdown = await generatePresignedDownloadUrl(sessionId, 'md', expiresIn, version);
  } catch (error) {
    console.warn(`Failed to generate Markdown download link: ${error}`);
  }

  return links;
}
