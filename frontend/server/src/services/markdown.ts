/**
 * Markdown Service
 * Retrieves markdown content from S3 or AgentCore Memory
 */

import { getS3FileContent, getChartImageUrls } from './s3';
import { queryAgentCoreMemory } from './agentcore';

/**
 * Replace image paths in markdown with S3 presigned URLs
 */
async function replaceImagePaths(markdown: string, sessionId: string): Promise<string> {
  try {
    // Get all chart image URLs from S3
    const imageUrls = await getChartImageUrls(sessionId);

    if (Object.keys(imageUrls).length === 0) {
      console.log('⚠️  No chart images found in S3');
      return markdown;
    }

    // Find all image references in markdown
    // Pattern: ![alt text](path/to/image.png)
    const imagePattern = /!\[([^\]]*)\]\(([^)]+)\)/g;
    let updatedMarkdown = markdown;
    let match;
    let replacementCount = 0;

    // Reset regex state
    imagePattern.lastIndex = 0;

    while ((match = imagePattern.exec(markdown)) !== null) {
      const altText = match[1];
      const imagePath = match[2];

      // Skip if already an absolute URL (http/https)
      if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        continue;
      }

      // Extract filename from path
      const filename = imagePath.split('/').pop();

      if (filename && imageUrls[filename]) {
        // Use S3 presigned URL directly
        const s3Url = imageUrls[filename];
        const originalPattern = `![${altText}](${imagePath})`;
        const replacement = `![${altText}](${s3Url})`;

        updatedMarkdown = updatedMarkdown.replace(originalPattern, replacement);
        replacementCount++;
        console.log(`  Replacing: ${imagePath} → ${s3Url.substring(0, 80)}...`);
      }
    }

    if (replacementCount > 0) {
      console.log(`✅ Replaced ${replacementCount} image paths with S3 presigned URLs`);
    } else {
      console.log('⚠️  No matching image paths found to replace in markdown');
    }

    return updatedMarkdown;
  } catch (error) {
    console.error('Failed to replace image paths:', error);
    return markdown; // Return original markdown if replacement fails
  }
}

/**
 * Get markdown content for a research session
 * First tries S3, then falls back to AgentCore Memory
 */
export async function getMarkdownContent(sessionId: string, version: string = 'draft'): Promise<string> {
  // Strategy 1: Try to get from S3 (most reliable for completed research)
  try {
    console.log(`Attempting to fetch markdown from S3 for session: ${sessionId}, version: ${version}`);
    const markdownContent = await getS3FileContent(sessionId, 'md', version);
    console.log(`✅ Successfully retrieved markdown from S3 (${markdownContent.length} chars)`);

    // Replace image paths with S3 presigned URLs
    const markdownWithImages = await replaceImagePaths(markdownContent, sessionId);
    return markdownWithImages;
  } catch (s3Error) {
    console.warn(`S3 fetch failed, trying AgentCore Memory: ${s3Error}`);
  }

  // Strategy 2: Try AgentCore Memory (for in-progress or recent research)
  try {
    console.log(`Attempting to fetch markdown from AgentCore Memory for session: ${sessionId}`);
    const events = await queryAgentCoreMemory(sessionId, 'default_user', 100);

    // Find the most recent markdown artifact
    let markdownContent = '';

    for (const event of events.reverse()) {
      // Check if event has artifact data
      if (event.artifact && event.artifact.data) {
        const data = event.artifact.data;

        // Check if it's markdown content
        if (
          event.artifact.type === 'markdown' ||
          event.artifact.type === 'document' ||
          (typeof data === 'string' && data.includes('# '))
        ) {
          markdownContent = typeof data === 'string' ? data : JSON.stringify(data);
          break;
        }
      }

      // Also check in eventData for markdown content
      if (event.eventData) {
        const eventData = typeof event.eventData === 'string'
          ? JSON.parse(event.eventData)
          : event.eventData;

        if (eventData.markdown || eventData.draft_report || eventData.content) {
          markdownContent = eventData.markdown || eventData.draft_report || eventData.content;
          break;
        }
      }
    }

    if (markdownContent) {
      console.log(`✅ Successfully retrieved markdown from Memory (${markdownContent.length} chars)`);

      // Replace image paths with S3 presigned URLs
      const markdownWithImages = await replaceImagePaths(markdownContent, sessionId);
      return markdownWithImages;
    }
  } catch (memoryError) {
    console.error('AgentCore Memory fetch failed:', memoryError);
  }

  // If all strategies fail, return informative placeholder
  console.warn(`⚠️  Could not retrieve markdown for session: ${sessionId}`);
  return `# Research Document

The research document could not be loaded at this time.

**Session ID:** ${sessionId}

**Possible reasons:**
- The research is still in progress
- The document has not been uploaded to S3 yet
- The session ID may be incorrect

Please check the research status and try again later.`;
}

/**
 * Alternative: Get markdown from file system (if using local storage)
 * This would require access to the workspace directory from backend
 */
export async function getMarkdownFromFile(sessionId: string): Promise<string> {
  // This is a placeholder for file-based retrieval
  // Would need to implement file system access or S3 retrieval
  throw new Error('File-based markdown retrieval not implemented');
}
